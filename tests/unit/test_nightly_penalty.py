"""Tests for NightlyPenalty. Todoist and Habitica are mocked; time is fixed via `nightly_penalty.datetime`."""

import logging
import zoneinfo
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

import nightly_penalty
import tasks_cache
from config import Settings
from nightly_penalty import NightlyPenalty
from tasks_cache import TasksCache
from todoist_api import TodoistAPI

HABIT_ID = "habit-1"
UTC_TZ_INFO = {"timezone": "UTC", "hours": 0, "minutes": 0}


class Clock(datetime):
    """Replaces `nightly_penalty.datetime`; `now()` returns `Clock.current` (aware, UTC) in the requested timezone."""

    current = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.current.astimezone(tz)


def at(day: int, hour: int, minute: int = 0, tz: timezone = timezone.utc) -> datetime:
    return datetime(2025, 6, day, hour, minute, tzinfo=tz).astimezone(timezone.utc)


def overdue(content: str, *labels: str) -> dict:
    return {"id": content, "content": content, "labels": list(labels)}


@pytest.fixture(name="db_file")
def fixture_db_file(tmp_path: Path) -> Path:
    return tmp_path / "cache.sqlite"


@pytest.fixture(autouse=True)
def fixture_clock():
    Clock.current = at(15, 12)
    with patch.object(nightly_penalty, "datetime", Clock):
        yield


@pytest.fixture(autouse=True)
def fixture_utc_zoneinfo():
    """Avoid depending on tzdata being installed; individual tests override this."""
    with patch.object(nightly_penalty, "ZoneInfo", side_effect=lambda name: timezone.utc if name == "UTC" else None):
        yield


@pytest.fixture(name="todoist")
def fixture_todoist() -> MagicMock:
    todoist = MagicMock(spec=TodoistAPI)
    todoist.get_user.return_value = {"id": 1001, "tz_info": UTC_TZ_INFO}
    todoist.get_overdue_tasks.return_value = []
    todoist.has_task_with_label.return_value = False
    return todoist


@pytest.fixture(name="habitica")
def fixture_habitica() -> MagicMock:
    habitica = MagicMock()
    habitica.user.tasks.return_value = [{"id": HABIT_ID, "text": "Unaccounted task", "type": "habit"}]
    return habitica


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "nightly_penalty_enabled": True,
        "penalty_time": "00:05",
        "penalty_window_hours": 4,
        "penalty_max_per_night": 5,
        "penalty_habit_name": "Unaccounted task",
        "penalty_exclude_labels": "Exclude,no_penalty",
        "penalty_pause_label": "pause_penalties",
    }
    values.update(overrides)
    return Settings(**values)


def make_cache(db_file: Path) -> TasksCache:
    with patch.object(tasks_cache, "get_settings", return_value=Settings(database_file=db_file)):
        return TasksCache()


def make_penalty(db_file: Path, todoist: MagicMock, habitica: MagicMock, **settings) -> NightlyPenalty:
    """A fresh instance (as after a restart) on the same database file."""
    return NightlyPenalty(make_settings(**settings), todoist, habitica, make_cache(db_file))


def taps(habitica: MagicMock) -> list[str]:
    return [call.args[0] for call in habitica.score_task.call_args_list if call.kwargs.get("direction") == "down"]


def started_yesterday(db_file: Path) -> None:
    """Simulate a service that has already been running, so the first-start rule does not apply."""
    cache = make_cache(db_file)
    cache.write_metadata("penalty_date", "2025-06-14")
    cache.write_metadata("penalty_target", "0")
    cache.write_metadata("penalty_done", "0")


def metadata(db_file: Path, key: str) -> str | None:
    return make_cache(db_file).read_metadata(key)


class TestDisabled:
    @staticmethod
    def should_be_off_by_default(db_file, todoist, habitica):
        settings = Settings(_env_file=None)
        assert settings.nightly_penalty_enabled is False

        penalty = NightlyPenalty(settings, todoist, habitica, make_cache(db_file))
        penalty.run()

        todoist.assert_not_called()
        assert not todoist.method_calls
        assert not habitica.method_calls
        assert metadata(db_file, "penalty_date") is None


class TestFirstStart:
    @staticmethod
    def should_only_record_today(db_file, todoist, habitica):
        todoist.get_overdue_tasks.return_value = [overdue("a"), overdue("b")]
        Clock.current = at(15, 1)  # inside tonight's window

        make_penalty(db_file, todoist, habitica).run()

        assert not taps(habitica)
        todoist.get_overdue_tasks.assert_not_called()
        assert metadata(db_file, "penalty_date") == "2025-06-15"
        assert metadata(db_file, "penalty_target") == "0"
        assert metadata(db_file, "penalty_done") == "0"

    @staticmethod
    def should_not_penalise_later_the_same_day(db_file, todoist, habitica):
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 1)
        make_penalty(db_file, todoist, habitica).run()

        Clock.current = at(15, 2)
        make_penalty(db_file, todoist, habitica).run()

        assert not taps(habitica)

    @staticmethod
    def should_penalise_from_next_night(db_file, todoist, habitica):
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 1)
        make_penalty(db_file, todoist, habitica).run()

        Clock.current = at(16, 0, 10)
        make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID]


class TestNightlyRun:
    @staticmethod
    def should_tap_once_per_counted_overdue_task(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a"), overdue("b", "home"), overdue("c")]
        Clock.current = at(15, 0, 10)

        make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID] * 3
        assert metadata(db_file, "penalty_target") == "3"
        assert metadata(db_file, "penalty_done") == "3"

    @staticmethod
    def should_cap_taps_per_night(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue(str(i)) for i in range(8)]
        Clock.current = at(15, 0, 10)

        cap = 5
        make_penalty(db_file, todoist, habitica, penalty_max_per_night=cap).run()

        assert len(taps(habitica)) == cap

    @staticmethod
    def should_ignore_tasks_with_excluded_labels_case_insensitively(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [
            overdue("counted", "home"),
            overdue("excluded", "exclude"),
            overdue("no-penalty", "No_Penalty"),
        ]
        Clock.current = at(15, 0, 10)

        make_penalty(db_file, todoist, habitica).run()

        assert len(taps(habitica)) == 1

    @staticmethod
    def should_wait_until_penalty_time(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 0, 4)

        make_penalty(db_file, todoist, habitica).run()

        assert not taps(habitica)
        todoist.get_overdue_tasks.assert_not_called()
        assert metadata(db_file, "penalty_date") == "2025-06-14"

    @staticmethod
    def should_skip_night_outside_window_and_never_charge_late(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 4, 6)  # 4h01m after 00:05

        make_penalty(db_file, todoist, habitica).run()
        Clock.current = at(15, 23, 0)
        make_penalty(db_file, todoist, habitica).run()

        assert not taps(habitica)
        todoist.get_overdue_tasks.assert_not_called()
        assert metadata(db_file, "penalty_date") == "2025-06-15"
        assert metadata(db_file, "penalty_target") == "0"

    @staticmethod
    def should_skip_night_when_pause_label_is_used(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        todoist.has_task_with_label.return_value = True
        Clock.current = at(15, 0, 10)

        make_penalty(db_file, todoist, habitica, penalty_pause_label="Pause_Penalties").run()

        assert not taps(habitica)
        todoist.has_task_with_label.assert_called_once_with("pause_penalties")
        assert metadata(db_file, "penalty_date") == "2025-06-15"

    @staticmethod
    def should_run_only_once_per_night(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a"), overdue("b")]
        Clock.current = at(15, 0, 10)
        make_penalty(db_file, todoist, habitica).run()

        Clock.current = at(15, 0, 11)
        make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID, HABIT_ID]
        todoist.get_overdue_tasks.assert_called_once()

    @staticmethod
    def should_retry_later_if_todoist_fails_before_night_starts(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.side_effect = [requests.ConnectionError("down"), [overdue("a")]]
        Clock.current = at(15, 0, 10)

        with pytest.raises(OSError):
            make_penalty(db_file, todoist, habitica).run()
        assert metadata(db_file, "penalty_date") == "2025-06-14"

        Clock.current = at(15, 0, 11)
        make_penalty(db_file, todoist, habitica).run()
        assert taps(habitica) == [HABIT_ID]


class TestResume:
    @staticmethod
    def should_resume_without_double_counting(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue(str(i)) for i in range(4)]
        habitica.score_task.side_effect = [None, None, requests.ConnectionError("down"), None, None, None]
        Clock.current = at(15, 0, 10)

        with pytest.raises(OSError):
            make_penalty(db_file, todoist, habitica).run()
        assert metadata(db_file, "penalty_target") == "4"
        assert metadata(db_file, "penalty_done") == "2"

        # After a restart, the target stays fixed even though the overdue list changed.
        todoist.get_overdue_tasks.return_value = [overdue(str(i)) for i in range(10)]
        Clock.current = at(15, 0, 20)
        make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID] * (2 + 1 + 2)  # 2 ok + 1 failed + 2 resumed
        assert metadata(db_file, "penalty_done") == "4"
        todoist.get_overdue_tasks.assert_called_once()

    @staticmethod
    def should_resume_even_after_window_closes(db_file, todoist, habitica):
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a"), overdue("b")]
        habitica.score_task.side_effect = [requests.ConnectionError("down"), None, None]
        Clock.current = at(15, 0, 10)
        with pytest.raises(OSError):
            make_penalty(db_file, todoist, habitica).run()

        Clock.current = at(15, 6, 0)  # target was fixed inside the window
        make_penalty(db_file, todoist, habitica).run()

        assert metadata(db_file, "penalty_done") == "2"


class TestHabit:
    @staticmethod
    def should_find_existing_habit_by_name_and_cache_its_id(db_file, todoist, habitica):
        started_yesterday(db_file)
        habitica.user.tasks.return_value = [
            {"id": "other", "text": "Something else"},
            {"id": HABIT_ID, "text": " Unaccounted task "},
        ]
        todoist.get_overdue_tasks.return_value = [overdue("a"), overdue("b")]
        Clock.current = at(15, 0, 10)

        make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID, HABIT_ID]
        habitica.user.tasks.assert_called_once_with(type="habits")
        assert metadata(db_file, "penalty_habit_id") == HABIT_ID

    @staticmethod
    def should_create_missing_habit(db_file, todoist, habitica):
        started_yesterday(db_file)
        habitica.user.tasks.side_effect = [[], {"id": "new-habit"}]
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 0, 10)

        make_penalty(db_file, todoist, habitica, penalty_habit_name="Slacked").run()

        habitica.user.tasks.assert_called_with(
            type="habit", text="Slacked", up=False, down=True, priority="1", _method="post"
        )
        assert taps(habitica) == ["new-habit"]

    @staticmethod
    @pytest.mark.parametrize(
        "not_found",
        [
            # How HabiticaAPI raises it: the response is positional, so `ex.response` is None.
            pytest.param(
                lambda: requests.HTTPError("404 Client Error: Not Found, JSON Payload: {}", object()),
                id="HabiticaAPI style",
            ),
            pytest.param(
                lambda: requests.HTTPError("Not Found", response=MagicMock(status_code=404)),
                id="with response",
            ),
        ],
    )
    def should_recreate_deleted_habit_on_404(db_file, todoist, habitica, not_found):
        started_yesterday(db_file)
        make_cache(db_file).write_metadata("penalty_habit_id", "deleted-habit")
        habitica.user.tasks.side_effect = [[], {"id": "new-habit"}]
        habitica.score_task.side_effect = [not_found(), None]
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 0, 10)

        make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == ["deleted-habit", "new-habit"]
        assert metadata(db_file, "penalty_habit_id") == "new-habit"
        assert metadata(db_file, "penalty_done") == "1"

    @staticmethod
    def should_not_loop_forever_if_recreated_habit_is_also_missing(db_file, todoist, habitica):
        started_yesterday(db_file)
        habitica.user.tasks.side_effect = lambda **kwargs: [] if kwargs.get("type") == "habits" else {"id": "new"}
        habitica.score_task.side_effect = requests.HTTPError("404 Client Error", object())
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 0, 10)

        with pytest.raises(requests.HTTPError):
            make_penalty(db_file, todoist, habitica).run()
        assert taps(habitica) == ["new", "new"]

    @staticmethod
    def should_raise_other_habitica_errors(db_file, todoist, habitica):
        started_yesterday(db_file)
        habitica.score_task.side_effect = requests.HTTPError("500 Server Error", object())
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        Clock.current = at(15, 0, 10)

        with pytest.raises(requests.HTTPError):
            make_penalty(db_file, todoist, habitica).run()
        assert metadata(db_file, "penalty_done") == "0"
        assert habitica.user.tasks.call_count == 1  # no re-creation


class TestTimezone:
    @staticmethod
    def should_use_zoneinfo_from_todoist_user(db_file, todoist, habitica):
        new_york = timezone(timedelta(hours=-4), "EDT")
        todoist.get_user.return_value = {"id": 1001, "tz_info": {"timezone": "America/New_York", "hours": -4}}
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a")]

        with patch.object(nightly_penalty, "ZoneInfo", return_value=new_york) as zone_info:
            Clock.current = at(15, 0, 10, tz=new_york)
            make_penalty(db_file, todoist, habitica).run()

        zone_info.assert_called_once_with("America/New_York")
        assert taps(habitica) == [HABIT_ID]
        assert metadata(db_file, "penalty_date") == "2025-06-15"

    @staticmethod
    def should_use_local_date_not_utc(db_file, todoist, habitica):
        tokyo = timezone(timedelta(hours=9))
        todoist.get_user.return_value = {"id": 1001, "tz_info": {"timezone": "Asia/Tokyo", "hours": 9}}
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a")]

        with patch.object(nightly_penalty, "ZoneInfo", return_value=tokyo):
            Clock.current = at(14, 15, 10)  # 00:10 on the 15th in Tokyo, still the 14th in UTC
            make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID]
        assert metadata(db_file, "penalty_date") == "2025-06-15"

    @staticmethod
    @pytest.mark.parametrize(
        "tz_info",
        [
            pytest.param({"timezone": "Mars/Olympus_Mons", "hours": 5, "minutes": 30}, id="unknown zone"),
            pytest.param({"hours": 5, "minutes": 30}, id="no zone name"),
        ],
    )
    def should_fall_back_to_fixed_offset_with_warning(db_file, todoist, habitica, caplog, tz_info):
        todoist.get_user.return_value = {"id": 1001, "tz_info": tz_info}
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        offset = timezone(timedelta(hours=5, minutes=30))

        with (
            patch.object(nightly_penalty, "ZoneInfo", side_effect=zoneinfo.ZoneInfoNotFoundError("nope")),
            caplog.at_level(logging.WARNING),
        ):
            Clock.current = at(15, 0, 4, tz=offset)
            make_penalty(db_file, todoist, habitica).run()
            assert not taps(habitica)
            Clock.current = at(15, 0, 6, tz=offset)
            make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID]
        assert "Using fixed UTC offset 5:30:00" in caplog.text

    @staticmethod
    @pytest.mark.skipif(
        "Europe/Prague" not in zoneinfo.available_timezones(), reason="tzdata not installed on this machine"
    )
    def should_work_with_real_zoneinfo(db_file, todoist, habitica):
        todoist.get_user.return_value = {"id": 1001, "tz_info": {"timezone": "Europe/Prague", "hours": 2}}
        started_yesterday(db_file)
        todoist.get_overdue_tasks.return_value = [overdue("a")]
        prague = zoneinfo.ZoneInfo("Europe/Prague")

        with patch.object(nightly_penalty, "ZoneInfo", zoneinfo.ZoneInfo):
            Clock.current = datetime(2025, 6, 15, 0, 10, tzinfo=prague).astimezone(timezone.utc)
            make_penalty(db_file, todoist, habitica).run()

        assert taps(habitica) == [HABIT_ID]


class TestSettings:
    @staticmethod
    @pytest.mark.parametrize("value, expected", [("00:05", (0, 5)), ("0:30", (0, 30)), ("23:59", (23, 59))])
    def should_parse_penalty_time(value, expected):
        run_at = make_settings(penalty_time=value).penalty_run_at
        assert (run_at.hour, run_at.minute) == expected

    @staticmethod
    @pytest.mark.parametrize("value", ["midnight", "24:00", "12", "1:2:3"])
    def should_reject_invalid_penalty_time(value):
        with pytest.raises(ValueError, match="HH:MM"):
            make_settings(penalty_time=value)

    @staticmethod
    def should_parse_exclude_labels():
        settings = make_settings(penalty_exclude_labels=" Exclude , no_penalty,,Later ")
        assert settings.penalty_exclude_label_set == {"exclude", "no_penalty", "later"}

    @staticmethod
    def should_have_documented_defaults(monkeypatch):
        names = (
            "NIGHTLY_PENALTY_ENABLED",
            "PENALTY_TIME",
            "PENALTY_WINDOW_HOURS",
            "PENALTY_MAX_PER_NIGHT",
            "PENALTY_HABIT_NAME",
            "PENALTY_EXCLUDE_LABELS",
            "PENALTY_PAUSE_LABEL",
        )
        for name in names:
            monkeypatch.delenv(name, raising=False)
        settings = Settings(_env_file=None)
        assert settings.model_dump(include={name.lower() for name in names}) == {
            "nightly_penalty_enabled": False,
            "penalty_time": "00:05",
            "penalty_window_hours": 4,
            "penalty_max_per_night": 5,
            "penalty_habit_name": "Unaccounted task",
            "penalty_exclude_labels": "Exclude,no_penalty",
            "penalty_pause_label": "pause_penalties",
        }
        assert settings.penalty_exclude_label_set == {"exclude", "no_penalty"}
