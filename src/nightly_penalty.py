"""Optional nightly penalty for overdue Todoist tasks. Off by default."""

import logging
from datetime import date, datetime, timedelta, timezone, tzinfo
from http import HTTPStatus
from zoneinfo import ZoneInfo

from requests import HTTPError

from config import Settings
from habitica_api import HabiticaAPI
from tasks_cache import TasksCache
from todoist_api import TodoistAPI


def _is_not_found(ex: HTTPError) -> bool:
    """HabiticaAPI wraps errors as `HTTPError(msg, res)`, so `ex.response` is usually None."""
    return (ex.response is not None and ex.response.status_code == HTTPStatus.NOT_FOUND) or "404" in str(ex)


class NightlyPenalty:
    """Once a night, taps a negative Habitica habit for each overdue Todoist task.

    Off by default. See the `NIGHTLY_PENALTY_ENABLED` and `PENALTY_*` settings in `config.Settings`.

    Progress is stored in the cache metadata, so a restart mid-night resumes without double counting:
    the target is fixed when the night starts and each tap is recorded as it is made.
    """

    _KEY_DATE = "penalty_date"
    _KEY_TARGET = "penalty_target"
    _KEY_DONE = "penalty_done"
    _KEY_HABIT_ID = "penalty_habit_id"

    def __init__(self, settings: Settings, todoist: TodoistAPI, habitica: HabiticaAPI, cache: TasksCache) -> None:
        self._todoist = todoist
        self._habitica = habitica
        self._cache = cache
        self._log = logging.getLogger(self.__class__.__name__)
        self.enabled = settings.nightly_penalty_enabled
        self._run_at = settings.penalty_run_at
        self._window = timedelta(hours=settings.penalty_window_hours)
        self._max_per_night = settings.penalty_max_per_night
        self._habit_name = settings.penalty_habit_name.strip()
        self._exclude_labels = settings.penalty_exclude_label_set
        self._pause_label = settings.penalty_pause_label.strip().lower()
        self._tz: tzinfo | None = None
        if self.enabled:
            self._log.info(
                f"Nightly penalty on: {self._run_at:%H:%M} local, up to {self._max_per_night} x "
                f"'{self._habit_name}'. Pause label: '{self._pause_label}'."
            )

    def _timezone(self) -> tzinfo:
        if self._tz is None:
            tz_info = self._todoist.get_user().get("tz_info") or {}
            try:
                self._tz = ZoneInfo(tz_info["timezone"])
            except (KeyError, TypeError, ValueError):  # ZoneInfoNotFoundError is a KeyError
                offset = timedelta(hours=int(tz_info.get("hours", 0)), minutes=int(tz_info.get("minutes", 0)))
                self._tz = timezone(offset)
                self._log.warning(f"Using fixed UTC offset {offset} for the nightly penalty.")
        return self._tz

    def _habit_id(self) -> str:
        if habit_id := self._cache.read_metadata(self._KEY_HABIT_ID):
            return habit_id
        habits = self._habitica.user.tasks(type="habits")
        habit = next((h for h in habits if h.get("text", "").strip() == self._habit_name), None)
        if habit is None:
            habit = self._habitica.user.tasks(
                type="habit", text=self._habit_name, up=False, down=True, priority="1", _method="post"
            )
            self._log.info(f"Created Habitica habit '{self._habit_name}'.")
        self._cache.write_metadata(self._KEY_HABIT_ID, habit["id"])
        return habit["id"]

    def _counted_tasks(self) -> list[dict]:
        """Overdue tasks that count towards the penalty."""
        return [
            task
            for task in self._todoist.get_overdue_tasks()
            if not {label.lower() for label in task.get("labels") or []} & self._exclude_labels
        ]

    def _nightly_target(self, today: date, late_by: timedelta) -> int:
        if late_by > self._window:
            self._log.info(f"Nightly penalty skipped for {today}: outside the window.")
            return 0
        if self._pause_label and self._todoist.has_task_with_label(self._pause_label):
            self._log.info(f"Nightly penalty paused for {today} (label '{self._pause_label}').")
            return 0
        counted = self._counted_tasks()
        names = ", ".join(f"'{task.get('content', '')}'" for task in counted) or "none"
        target = min(len(counted), self._max_per_night)
        self._log.info(f"Nightly check {today}: {len(counted)} unaccounted ({names}); penalising {target}.")
        return target

    def run(self) -> None:
        if not self.enabled:
            return
        now = datetime.now(self._timezone())
        today = now.date()
        last = self._cache.read_metadata(self._KEY_DATE)

        if last is None:  # first start: never penalise retroactively
            self._begin_night(today, 0)
            self._log.info("Nightly penalty starts tomorrow night.")
            return

        if last != today.isoformat():
            start = datetime.combine(today, self._run_at, tzinfo=now.tzinfo)
            if now < start:
                return
            self._begin_night(today, self._nightly_target(today, now - start))

        self._apply_remaining()

    def _begin_night(self, day: date, target: int) -> None:
        self._cache.write_metadata(self._KEY_DATE, day.isoformat())
        self._cache.write_metadata(self._KEY_TARGET, str(target))
        self._cache.write_metadata(self._KEY_DONE, "0")

    def _apply_remaining(self) -> None:
        target = int(self._cache.read_metadata(self._KEY_TARGET, "0") or 0)
        done = int(self._cache.read_metadata(self._KEY_DONE, "0") or 0)
        recreated = False
        while done < target:
            habit_id = self._habit_id()
            try:
                self._habitica.score_task(habit_id, direction="down")
            except HTTPError as ex:
                if recreated or not _is_not_found(ex):
                    raise
                self._log.warning(f"Habitica habit '{self._habit_name}' not found. Re-creating.")
                self._cache.write_metadata(self._KEY_HABIT_ID, "")
                recreated = True
                continue
            done += 1
            self._cache.write_metadata(self._KEY_DONE, str(done))
            self._log.info(f"Nightly penalty {done}/{target}: '{self._habit_name}' -1.")
