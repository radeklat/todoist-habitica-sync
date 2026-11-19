"""Tests for the Todoist API v1 client. All HTTP is mocked via `requests.Session.get`."""

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
import requests

import todoist_api
from models.todoist import TodoistPriority
from todoist_api import TodoistAPI

OWN_ID = "1001"
OTHER_ID = "2002"
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
LAST_SYNC = "2025-06-15T10:00:00.000000Z"

ACTIVITIES = "/api/v1/activities"
COMPLETED = "/api/v1/tasks/completed/by_completion_date"
USER = "/api/v1/user"
TASKS_FILTER = "/api/v1/tasks/filter"
MAX_PAGE_SIZE = 200  # Todoist API v1 limit for activities and tasks/filter


def make_response(status: int = 200, payload: dict | None = None, url: str = "") -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(payload or {}).encode()  # pylint: disable=protected-access
    response.url = url
    return response


class FakeTodoist:
    """Routes `Session.get` calls by URL path and records them."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.routes: dict[str, Callable[[dict], requests.Response]] = {
            USER: lambda params: make_response(payload={"id": int(OWN_ID), "tz_info": {"timezone": "UTC"}}),
        }

    def route(self, path: str, *responses: requests.Response | dict) -> None:
        """Serve the given responses in order; the last one repeats."""
        queue = [resp if isinstance(resp, requests.Response) else make_response(payload=resp) for resp in responses]

        def handler(_params: dict) -> requests.Response:
            return queue.pop(0) if len(queue) > 1 else queue[0]

        self.routes[path] = handler

    def get(self, url: str, headers: dict | None = None, params: dict | None = None) -> requests.Response:
        path = urlparse(url).path
        self.calls.append((path, dict(params or {})))
        assert headers == {"Authorization": "Bearer token"}
        return self.routes[path](params or {})

    def calls_to(self, path: str) -> list[dict]:
        return [params for call_path, params in self.calls if call_path == path]


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz)


@pytest.fixture(name="fake")
def fixture_fake():
    fake = FakeTodoist()
    with (
        patch.object(requests.Session, "get", autospec=True, side_effect=lambda _self, *a, **kw: fake.get(*a, **kw)),
        patch.object(todoist_api, "datetime", FixedDatetime),
    ):
        yield fake


def event(
    object_id: str = "task-1",
    event_date: str = "2025-06-15T11:00:00.000000Z",
    initiator_id: str | int | None = OWN_ID,
    object_type: str | None = "item",
    **extra,
) -> dict:
    return {
        "object_type": object_type,
        "object_id": object_id,
        "event_type": "completed",
        "event_date": event_date,
        "initiator_id": initiator_id,
        "extra_data": {"content": "Do the thing", "priority": 4, "labels": ["home"], **extra},
    }


def completed_item(item_id: str = "task-9", completed_at: str = "2025-06-15T11:30:00.000000Z", **fields) -> dict:
    return {
        "id": item_id,
        "user_id": OWN_ID,
        "content": "Fallback task",
        "priority": 2,
        "labels": [],
        "checked": True,
        "is_deleted": False,
        "completed_at": completed_at,
        "due": None,
        **fields,
    }


def synced(api: TodoistAPI) -> list:
    return list(api.iter_pop_newly_completed_tasks())


class TestActivityLogParsing:
    @staticmethod
    def should_build_completed_task_from_event(fake):
        fake.route(ACTIVITIES, {"results": [event(is_recurring=True, due_date="2025-06-15")]})
        api = TodoistAPI("token", LAST_SYNC)

        last_sync = api.sync()
        (task,) = synced(api)

        assert task.task_id == "task-1"
        assert task.user_id == OWN_ID
        assert task.completed_at == "2025-06-15T11:00:00.000000Z"
        assert task.item_object.content == "Do the thing"
        assert task.item_object.priority == TodoistPriority.P1.value
        assert task.item_object.labels == ["home"]
        assert task.item_object.is_recurring
        assert last_sync == "2025-06-15T11:00:00.000000Z"

    @staticmethod
    def should_fill_defaults_for_minimal_event(fake):
        fake.route(
            ACTIVITIES,
            {"results": [{"object_id": 7, "event_date": "2025-06-15T11:00:00Z", "initiator_id": int(OWN_ID)}]},
        )
        api = TodoistAPI("token", LAST_SYNC)

        api.sync()
        (task,) = synced(api)

        assert task.task_id == "7"
        assert task.item_object.content == ""
        assert task.item_object.priority == 1
        assert task.item_object.labels == []
        assert not task.item_object.is_recurring

    @staticmethod
    def should_send_expected_query(fake):
        fake.route(ACTIVITIES, {"results": []})
        TodoistAPI("token", LAST_SYNC).sync()

        (params,) = fake.calls_to(ACTIVITIES)
        assert json.loads(params["object_event_types"]) == ["item:completed"]
        assert isinstance(params["object_event_types"], str)  # JSON-encoded string, as the official SDK sends it
        assert params["initiator_id"] == OWN_ID
        assert params["date_from"] == LAST_SYNC
        assert params["limit"] <= MAX_PAGE_SIZE

    @staticmethod
    def should_follow_cursor_pagination(fake):
        fake.route(
            ACTIVITIES,
            {"results": [event("a", "2025-06-15T10:30:00Z")], "next_cursor": "page-2"},
            {"results": [event("b", "2025-06-15T11:30:00Z")], "next_cursor": None},
        )
        api = TodoistAPI("token", LAST_SYNC)

        assert api.sync() == "2025-06-15T11:30:00.000000Z"

        assert sorted(task.task_id for task in synced(api)) == ["a", "b"]
        assert [params.get("cursor") for params in fake.calls_to(ACTIVITIES)] == [None, "page-2"]

    @staticmethod
    @pytest.mark.parametrize(
        "bad_event",
        [
            pytest.param(event(object_type="note"), id="not a task"),
            pytest.param(event(event_date=""), id="no event date"),
        ],
    )
    def should_skip_events_that_are_not_task_completions(fake, bad_event):
        fake.route(ACTIVITIES, {"results": [bad_event]})
        api = TodoistAPI("token", LAST_SYNC)
        api.sync()
        assert not synced(api)

    @staticmethod
    def should_raise_on_invalid_token(fake):
        fake.route(ACTIVITIES, make_response(401))
        with pytest.raises(RuntimeError, match="Invalid API token"):
            TodoistAPI("token", LAST_SYNC).sync()

    @staticmethod
    def should_fetch_own_user_once(fake):
        fake.route(ACTIVITIES, {"results": []})
        api = TodoistAPI("token", LAST_SYNC)
        api.sync()
        api.sync()
        assert len(fake.calls_to(USER)) == 1


class TestOwnUserFilter:
    @staticmethod
    def should_skip_completions_by_collaborators(fake):
        fake.route(
            ACTIVITIES,
            {
                "results": [
                    event("mine", initiator_id=OWN_ID),
                    event("theirs", initiator_id=OTHER_ID),
                    event("mine-int", initiator_id=int(OWN_ID)),
                ]
            },
        )
        api = TodoistAPI("token", LAST_SYNC)
        api.sync()
        assert sorted(task.task_id for task in synced(api)) == ["mine", "mine-int"]

    @staticmethod
    @pytest.mark.parametrize(
        "item, counted",
        [
            pytest.param(completed_item(), True, id="unassigned"),
            pytest.param(completed_item(responsible_uid=OWN_ID), True, id="assigned to me"),
            pytest.param(completed_item(responsible_uid=OTHER_ID), False, id="assigned to someone else"),
            pytest.param(completed_item(completed_by_uid=OWN_ID), True, id="completed by me"),
            pytest.param(
                completed_item(completed_by_uid=OTHER_ID, responsible_uid=OWN_ID), False, id="completed by someone else"
            ),
        ],
    )
    def should_apply_to_fallback_endpoint(fake, item, counted):
        fake.route(ACTIVITIES, make_response(403))
        fake.route(COMPLETED, {"items": [item]})
        api = TodoistAPI("token", LAST_SYNC)
        api.sync()
        assert bool(synced(api)) is counted


class TestDuplicateFiltering:
    @staticmethod
    def should_keep_only_completions_strictly_newer_than_last_sync(fake):
        fake.route(
            ACTIVITIES,
            {
                "results": [
                    event("older", "2025-06-15T09:59:59Z"),
                    event("same", LAST_SYNC),
                    event("same-other-format", "2025-06-15T12:00:00+02:00"),  # == 10:00 UTC
                    event("newer", "2025-06-15T10:00:01Z"),
                ]
            },
        )
        api = TodoistAPI("token", LAST_SYNC)
        api.sync()
        assert [task.task_id for task in synced(api)] == ["newer"]

    @staticmethod
    def should_not_return_same_completion_twice(fake):
        fake.route(ACTIVITIES, {"results": [event("a", "2025-06-15T11:00:00Z")]})
        api = TodoistAPI("token", LAST_SYNC)

        api.sync()
        assert len(synced(api)) == 1

        assert api.sync() == "2025-06-15T11:00:00.000000Z"  # inclusive date_from returns it again
        assert not synced(api)
        assert fake.calls_to(ACTIVITIES)[-1]["date_from"] == "2025-06-15T11:00:00.000000Z"

    @staticmethod
    def should_advance_last_sync_to_newest_completion_regardless_of_order(fake):
        fake.route(ACTIVITIES, {"results": [event("b", "2025-06-15T11:30:00Z"), event("a", "2025-06-15T10:30:00Z")]})
        assert TodoistAPI("token", LAST_SYNC).sync() == "2025-06-15T11:30:00.000000Z"

    @staticmethod
    def should_keep_last_sync_when_nothing_new(fake):
        fake.route(ACTIVITIES, {"results": []})
        assert TodoistAPI("token", LAST_SYNC).sync() == LAST_SYNC

    @staticmethod
    def should_start_from_now_without_last_sync(fake):
        fake.route(ACTIVITIES, {"results": []})
        assert TodoistAPI("token", None).sync() == "2025-06-15T12:00:00.000000Z"

    @staticmethod
    def should_cap_lookback_window(fake, caplog):
        fake.route(ACTIVITIES, {"results": []})
        with caplog.at_level(logging.WARNING):
            TodoistAPI("token", "2024-01-01T00:00:00Z").sync()
        (params,) = fake.calls_to(ACTIVITIES)
        assert params["date_from"] == todoist_api._fmt(NOW - timedelta(days=89))  # pylint: disable=protected-access
        assert "only the last 89 days" in caplog.text


class TestFallback:
    @staticmethod
    @pytest.mark.parametrize("status", [400, 403, 404, 410])
    def should_fall_back_to_completed_endpoint_on_4xx(fake, caplog, status):
        fake.route(ACTIVITIES, make_response(status))
        fake.route(COMPLETED, {"items": [completed_item()], "next_cursor": None})
        api = TodoistAPI("token", LAST_SYNC)

        with caplog.at_level(logging.WARNING):
            assert api.sync() == "2025-06-15T11:30:00.000000Z"

        (task,) = synced(api)
        assert task.task_id == "task-9"
        assert task.item_object.content == "Fallback task"
        assert f"Activity log unavailable ({status})" in caplog.text
        (params,) = fake.calls_to(COMPLETED)
        assert params["since"] == LAST_SYNC
        assert params["until"] == "2025-06-15T12:00:00.000000Z"

    @staticmethod
    def should_stay_on_fallback_after_switching(fake):
        fake.route(ACTIVITIES, make_response(403))
        fake.route(COMPLETED, {"items": []})
        api = TodoistAPI("token", LAST_SYNC)
        api.sync()
        api.sync()
        assert [path for path, _params in fake.calls] == [USER, ACTIVITIES, COMPLETED, COMPLETED]

    @staticmethod
    def should_filter_fallback_duplicates_too(fake):
        fake.route(ACTIVITIES, make_response(403))
        fake.route(COMPLETED, {"items": [completed_item("old", LAST_SYNC), completed_item("new")]})
        api = TodoistAPI("token", LAST_SYNC)
        api.sync()
        assert [task.task_id for task in synced(api)] == ["new"]

    @staticmethod
    @pytest.mark.parametrize("status", [429, 500, 503])
    def should_not_fall_back_on_rate_limit_or_server_error(fake, status):
        fake.route(ACTIVITIES, make_response(status), {"results": [event()]})
        api = TodoistAPI("token", LAST_SYNC)

        with pytest.raises(requests.HTTPError):
            api.sync()

        api.sync()  # next loop retries the activity log
        assert len(synced(api)) == 1
        assert not fake.calls_to(COMPLETED)


class TestOtherEndpoints:
    @staticmethod
    def should_query_overdue_tasks_for_me_or_unassigned(fake):
        fake.route(TASKS_FILTER, {"results": [{"id": "1"}], "next_cursor": "x"}, {"results": [{"id": "2"}]})
        assert [task["id"] for task in TodoistAPI("token").get_overdue_tasks()] == ["1", "2"]
        assert fake.calls_to(TASKS_FILTER)[0]["query"] == "overdue & (assigned to: me | !assigned)"
        assert fake.calls_to(TASKS_FILTER)[0]["limit"] <= MAX_PAGE_SIZE

    @staticmethod
    @pytest.mark.parametrize("results, expected", [([{"id": "1"}], True), ([], False)])
    def should_check_for_label(fake, results, expected):
        fake.route(TASKS_FILTER, {"results": results})
        assert TodoistAPI("token").has_task_with_label("pause_penalties") is expected
        assert fake.calls_to(TASKS_FILTER)[0]["query"] == "@pause_penalties"
