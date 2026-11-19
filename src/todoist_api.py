"""Todoist API v1 client.

Todoist retired the v9 Sync API (`sync/v9/completed/get_all` now returns 410 Gone).

Completions are read from the v1 activity log (`/api/v1/activities`), which records every completion,
including each occurrence of a recurring task. If the activity log returns a 4xx, it falls back to
`/api/v1/tasks/completed/by_completion_date`, which skips completions of recurring tasks that are still active.

See Also: https://developer.todoist.com/api/v1/
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

import requests
from dateutil.parser import isoparse

from models.todoist import CompletedTodoistTask

# Todoist caps how far back the completed endpoint can look (3 months).
_MAX_WINDOW = timedelta(days=89)

_INVALID_TOKEN_MESSAGE = (
    "Invalid API token for Todoist. Please check that is matches the one "
    "from https://todoist.com/app/settings/integrations/developer."
)


def _to_utc(value: str) -> datetime:
    parsed = isoparse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _is_own_completion(item: dict, user_id: str) -> bool:
    """Whether a completed task from the fallback endpoint counts for the token owner.

    Uses who completed it when the API says so, otherwise who it is assigned to. Unassigned tasks count.
    """
    for field in ("completed_by_uid", "responsible_uid"):
        if (uid := item.get(field)) is not None:
            return str(uid) == user_id
    return True


class TodoistAPI:
    _BASE_URL = "https://api.todoist.com/api/v1"
    _ENDPOINT_ACTIVITIES = f"{_BASE_URL}/activities"
    _ENDPOINT_COMPLETED = f"{_BASE_URL}/tasks/completed/by_completion_date"
    _ENDPOINT_USER = f"{_BASE_URL}/user"
    _ENDPOINT_TASKS_FILTER = f"{_BASE_URL}/tasks/filter"

    def __init__(self, token: str, last_sync_datetime_utc: str | None = None) -> None:
        self._session = requests.Session()
        self._headers = {"Authorization": f"Bearer {token}"}
        self._last_sync_datetime_utc: str | None = last_sync_datetime_utc
        self._completed_tasks: list[CompletedTodoistTask] = []
        self._use_activity_log = True
        self._user: dict | None = None
        self._log = logging.getLogger(self.__class__.__name__)

    def iter_pop_newly_completed_tasks(self) -> Iterator[CompletedTodoistTask]:
        """Iterate over newly completed tasks and remove them from the internal list."""
        while self._completed_tasks:
            yield self._completed_tasks.pop()

    def _get_pages(self, url: str, params: dict, results_field: str) -> list[dict]:
        results: list[dict] = []
        cursor: str | None = None
        while True:
            page_params = dict(params, **({"cursor": cursor} if cursor else {}))
            response = self._session.get(url, headers=self._headers, params=page_params)

            if response.status_code == HTTPStatus.UNAUTHORIZED:
                raise RuntimeError(_INVALID_TOKEN_MESSAGE)
            response.raise_for_status()

            data = response.json()
            results.extend(data.get(results_field) or [])
            cursor = data.get("next_cursor")
            if not cursor:
                return results

    @staticmethod
    def _task(task_id: str, user_id: str, completed_at: str, item: dict) -> CompletedTodoistTask:
        task = dict(item)
        task["id"] = task_id
        task.setdefault("content", "")
        task.setdefault("priority", 1)
        task["labels"] = task.get("labels") or []
        task.setdefault("checked", True)
        task.setdefault("is_deleted", False)
        if isinstance(due := task.get("due"), dict):
            if not due.get("date"):
                due["date"] = completed_at
            due.setdefault("string", "")
            due.setdefault("lang", "en")
            due.setdefault("is_recurring", False)
        else:
            task["due"] = None
        return CompletedTodoistTask(task_id=task_id, user_id=user_id, completed_at=completed_at, item_object=task)

    def get_user(self) -> dict:
        """Own Todoist user (fetched once)."""
        if self._user is None:
            response = self._session.get(self._ENDPOINT_USER, headers=self._headers)
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                raise RuntimeError(_INVALID_TOKEN_MESSAGE)
            response.raise_for_status()
            self._user = response.json()
            self._log.info(f"Scoring only tasks completed by Todoist user {self._user['id']}.")
        return self._user

    def _get_user_id(self) -> str:
        """Own user ID, so completions by collaborators in shared projects are not scored."""
        return str(self.get_user()["id"])

    def get_overdue_tasks(self) -> list[dict]:
        """Active tasks that are overdue and assigned to the user or to no one."""
        return self._get_pages(
            self._ENDPOINT_TASKS_FILTER,
            {"query": "overdue & (assigned to: me | !assigned)", "limit": 200},
            "results",
        )

    def has_task_with_label(self, label: str) -> bool:
        """Whether any active task has the given label."""
        return bool(self._get_pages(self._ENDPOINT_TASKS_FILTER, {"query": f"@{label}", "limit": 1}, "results"))

    def _from_activity_log(self, since: datetime) -> list[CompletedTodoistTask]:
        user_id = self._get_user_id()
        events = self._get_pages(
            self._ENDPOINT_ACTIVITIES,
            {
                "object_event_types": json.dumps(["item:completed"]),
                "date_from": _fmt(since),
                "initiator_id": user_id,
                "limit": 100,
            },
            "results",
        )
        tasks = []
        for event in events:
            if not event.get("event_date") or event.get("object_type") not in (None, "item", "task"):
                continue
            if event.get("initiator_id") is not None and str(event["initiator_id"]) != user_id:
                continue
            extra = event.get("extra_data") or {}
            tasks.append(
                self._task(
                    str(event["object_id"]),
                    str(event.get("initiator_id") or ""),
                    event["event_date"],
                    {
                        "content": extra.get("content", ""),
                        "priority": extra.get("priority", 1),
                        "labels": extra.get("labels") or [],
                        "due": {
                            "date": extra.get("due_date") or event["event_date"],
                            "is_recurring": bool(extra.get("is_recurring", False)),
                        },
                    },
                )
            )
        return tasks

    def _from_completed_endpoint(self, since: datetime, until: datetime) -> list[CompletedTodoistTask]:
        user_id = self._get_user_id()
        items = self._get_pages(
            self._ENDPOINT_COMPLETED,
            {"since": _fmt(since), "until": _fmt(until), "limit": 200},
            "items",
        )
        return [
            self._task(str(item["id"]), str(item.get("user_id", "")), item["completed_at"], item)
            for item in items
            if item.get("completed_at") and _is_own_completion(item, user_id)
        ]

    def _should_fall_back(self, ex: requests.HTTPError) -> bool:
        """Whether an activity log error means it is unavailable, rather than a temporary failure."""
        status = ex.response.status_code if ex.response is not None else None
        is_client_error = status is not None and HTTPStatus.BAD_REQUEST <= status < HTTPStatus.INTERNAL_SERVER_ERROR
        if not is_client_error or status == HTTPStatus.TOO_MANY_REQUESTS:
            return False
        self._log.warning(
            f"Activity log unavailable ({status}); falling back to the completed tasks "
            "endpoint, which does not include recurring tasks."
        )
        return True

    def sync(self) -> str | None:
        """Sync recently completed tasks.

        Returns: Last sync datetime to persist.
        """
        until = datetime.now(timezone.utc)
        since = _to_utc(self._last_sync_datetime_utc) if self._last_sync_datetime_utc else until
        if until - since > _MAX_WINDOW:
            self._log.warning("Last sync is older than the API allows; only the last 89 days are checked.")
            since = until - _MAX_WINDOW

        found: list[CompletedTodoistTask] | None = None
        if self._use_activity_log:
            try:
                found = self._from_activity_log(since)
            except requests.HTTPError as ex:
                if not self._should_fall_back(ex):
                    raise
                self._use_activity_log = False
        if found is None:
            found = self._from_completed_endpoint(since, until)

        # Date filters are inclusive, so keep only completions strictly newer than the last sync.
        newly_completed_tasks = sorted(
            (task for task in found if _to_utc(task.completed_at) > since),
            key=lambda task: _to_utc(task.completed_at),
        )

        if newly_completed_tasks:
            self._log.info(f"Synced {len(newly_completed_tasks)} new completed tasks.")
            self._last_sync_datetime_utc = _fmt(_to_utc(newly_completed_tasks[-1].completed_at))
            self._completed_tasks.extend(newly_completed_tasks)
        else:
            self._log.debug("No new completed tasks.")
            if self._last_sync_datetime_utc is None:
                self._last_sync_datetime_utc = _fmt(since)

        return self._last_sync_datetime_utc
