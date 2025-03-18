from typing import Iterator

import requests
from pydantic import BaseModel

from models.todoist import CompletedTodoistTask


class QueryParamsCompletedGetAll(BaseModel):
    """See https://developer.todoist.com/sync/v9/#get-all-completed-items."""

    limit: int = 200
    since: str | None
    annotate_items: bool = True


class TodoistAPI:
    _SYNC_VERSION = "v9"
    _BASE_URL = f"https://api.todoist.com/sync/{_SYNC_VERSION}"
    _ENDPOINT_COMPLETED_GET_ALL = f"{_BASE_URL}/completed/get_all"

    def __init__(self, token: str, last_sync_datetime_utc: str | None = None) -> None:
        self._session = requests.Session()
        self._headers = {"Authorization": f"Bearer {token}"}
        self._last_sync_datetime_utc: str | None = last_sync_datetime_utc
        self._completed_tasks: list[CompletedTodoistTask] = []

    def iter_pop_newly_completed_tasks(self) -> Iterator[CompletedTodoistTask]:
        """Pop tasks from last sync."""
        while self._completed_tasks:
            yield self._completed_tasks.pop()

    def sync(self) -> str | None:
        """Sync recently completed tasks.

        Returns: Last sync datetime to persist.
        """
        response = self._session.get(
            self._ENDPOINT_COMPLETED_GET_ALL,
            headers=self._headers,
            params=QueryParamsCompletedGetAll(since=self._last_sync_datetime_utc).model_dump(exclude_none=True),
        )

        if response.status_code == 403:
            raise RuntimeError(
                "Invalid API token for Todoist. Please check that is matches the one "
                "from https://todoist.com/app/settings/integrations/developer."
            )

        response.raise_for_status()

        if newly_completed_tasks := [CompletedTodoistTask(**data) for data in response.json()["items"]]:
            self._last_sync_datetime_utc = newly_completed_tasks[0].completed_at
            self._completed_tasks.extend(newly_completed_tasks)

        return self._last_sync_datetime_utc
