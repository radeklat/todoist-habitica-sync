from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Final

from pydantic import BaseModel, ConfigDict
from requests import HTTPError

from config import Settings, get_settings
from delay import DelayTimer
from habitica_api import HabiticaAPI, HabiticaAPIHeaders
from models.generic_task import GenericTask
from models.habitica import HabiticaDifficulty
from models.todoist import TodoistPriority, TodoistTask
from tasks_cache import TasksCache
from todoist_api import TodoistAPI

_LOGGER = logging.getLogger(__name__)


class FSMState(BaseModel):
    context: TasksSync
    generic_task: GenericTask
    optional_todoist_task: TodoistTask | None = None

    _STATES: Final[dict[str, type[FSMState]]] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _set_state(self, state_cls: type[FSMState]) -> None:
        if self.__class__ is not state_cls:  # transition to a different state
            self.context.set_state(state_cls(**self.model_dump()))

    def next_state(self) -> None:
        raise NotImplementedError

    @classmethod
    def name(cls) -> str:
        return cls.__name__.replace("State", "")

    @property
    def todoist_task(self) -> TodoistTask:
        if self.optional_todoist_task is None:
            raise RuntimeError("optional_todoist_task is not set but required by the state transition.")
        return self.optional_todoist_task

    @classmethod
    def register(cls, state_cls: type[FSMState]) -> None:
        cls._STATES[state_cls.name()] = state_cls

    @classmethod
    def factory(
        cls,
        context: TasksSync,
        generic_task: GenericTask,
        optional_todoist_task: TodoistTask | None = None,
    ) -> FSMState:
        state_name = generic_task.state
        state = cls._STATES[state_name](
            context=context,
            generic_task=generic_task,
            optional_todoist_task=optional_todoist_task,
        )
        return state


class StateTodoist(FSMState):
    def next_state(self) -> None:
        raise NotImplementedError

    def _owned_by_me(self) -> bool:
        if self.context.todoist_user_id is None or self.todoist_task.responsible_uid is None:
            return True
        return self.todoist_task.responsible_uid == self.context.todoist_user_id


class StateTodoistNew(StateTodoist):
    def next_state(self) -> None:
        if self.todoist_task.is_deleted or (self.todoist_task.checked and self.context.initial_sync):
            # Task has been already deleted or checked previously and this is an initial sync
            self._set_state(StateHidden)
        else:
            # task has not been completed ever or since last sync
            self._set_state(StateTodoistActive)


class StateTodoistActive(StateTodoist):
    def _should_task_score_points(self) -> bool:
        if self.todoist_task.is_recurring:
            recurring_task_has_been_checked = bool(
                (
                    # The due date has moved since the last time we checked -> the task has been checked OR rescheduled
                    self.generic_task.due_date_utc_timestamp
                    and self.todoist_task.due_date_utc_timestamp
                    and self.generic_task.due_date_utc_timestamp < self.todoist_task.due_date_utc_timestamp
                    # The due date has moved to the future -> the task has been checked
                    and self.todoist_task.due_date_utc_timestamp > int(datetime.now(timezone.utc).timestamp())
                )
                # If completed_at is set, it has been permanently finished
                or self.todoist_task.completed_at is not None
            )

            if recurring_task_has_been_checked:
                self.generic_task.due_date_utc_timestamp = self.todoist_task.due_date_utc_timestamp
                self.generic_task.completed_at = self.todoist_task.completed_at
                return True

        if self.todoist_task.checked:
            return True

        return False

    def next_state(self) -> None:
        if self.todoist_task.is_deleted:
            self._set_state(StateHidden)
        elif self._should_task_score_points():
            if self._owned_by_me():
                self.generic_task.content = self.todoist_task.content
                self.generic_task.priority = self.todoist_task.priority
                self._set_state(StateHabiticaNew)
            else:
                self._set_state(StateHidden)
        else:
            self._set_state(StateTodoistActive)


class StateHabiticaNew(FSMState):
    def next_state(self) -> None:
        self.context.create_habitica_task(self.generic_task)
        self._set_state(StateHabiticaCreated)


class StateHabiticaCreated(FSMState):
    def next_state(self) -> None:
        try:
            self.context.habitica.score_task(self.generic_task.get_habitica_task_id())
            next_state: type[FSMState] = StateHabiticaFinished
        except HTTPError as ex:
            if ex.response is not None and ex.response.status_code == 404:
                next_state = StateHabiticaNew
                _LOGGER.warning(f"Habitica task '{self.generic_task.content}' not found. Re-setting state.")
            else:
                raise ex

        self._set_state(next_state)


class StateHabiticaFinished(FSMState):
    def next_state(self) -> None:
        try:
            self.context.habitica.delete_task(self.generic_task.get_habitica_task_id())
        except HTTPError as ex:
            if ex.response is not None and ex.response.status_code == 404:
                _LOGGER.warning(f"Habitica task '{self.generic_task.content}' not found.")
            else:
                raise ex

        if self.generic_task.is_recurring and not self.generic_task.completed_at:
            next_state: type[FSMState] = StateTodoistActive
        else:
            next_state = StateHidden

        self._set_state(next_state)


class StateHidden(FSMState):
    def next_state(self) -> None:
        pass  # no action


FSMState.register(StateTodoistNew)
FSMState.register(StateTodoistActive)
FSMState.register(StateHabiticaNew)
FSMState.register(StateHabiticaCreated)
FSMState.register(StateHabiticaFinished)
FSMState.register(StateHidden)


class TasksSync:  # pylint: disable=too-few-public-methods
    """Class managing tasks synchronisation.

    Todoist API: https://developer.todoist.com/sync/v7/?python#overview
    Habitica API: https://habitica.com/apidoc
    """

    def __init__(self):
        settings = get_settings()

        self.habitica = HabiticaAPI(
            HabiticaAPIHeaders(user_id=settings.habitica_user_id, api_key=settings.habitica_api_key)
        )

        self._log = logging.getLogger(self.__class__.__name__)

        self._todoist = TodoistAPI(settings.todoist_api_key)
        self._todoist_user_id = settings.todoist_user_id

        self._task_cache = TasksCache(
            habitica_dirty_states={_.name() for _ in [StateHabiticaNew, StateHabiticaCreated, StateHabiticaFinished]}
        )
        self._sync_sleep: Final[DelayTimer] = DelayTimer(
            settings.sync_delay_seconds, "Next check in {delay:.0f} seconds."
        )

    def run_forever(self) -> None:
        while True:
            try:
                self._todoist.sync()
                self._next_tasks_state()
            except OSError as ex:
                self._log.error(f"Unexpected network error: {ex}")

            try:
                self._sync_sleep()
            except KeyboardInterrupt:
                break

    def set_state(self, state: FSMState) -> None:
        new_state = state.name()
        if state.generic_task.state != new_state:
            self._log.info(f"'{state.generic_task.content}' {state.generic_task.state} -> {new_state}")
            state.generic_task.state = new_state
            self._task_cache.save_task(state.generic_task)

    def create_habitica_task(self, generic_task: GenericTask) -> None:
        previous_habitica_id = generic_task.habitica_task_id
        difficulty = self._get_task_difficulty(
            get_settings(),
            self._todoist.state.items[generic_task.todoist_task_id].labels,
            generic_task.priority_enum,
        )
        generic_task.habitica_task_id = self.habitica.create_task(generic_task.content, difficulty)["id"]
        self._task_cache.save_task(generic_task, previous_habitica_id)

    @staticmethod
    def _get_task_difficulty(settings: Settings, labels: list[str], priority: TodoistPriority) -> HabiticaDifficulty:
        label_difficulties = [
            settings.label_to_difficulty[label_lower]
            for label in labels
            if (label_lower := label.lower()) in settings.label_to_difficulty
        ]
        if label_difficulties:
            return max(label_difficulties)
        return settings.priority_to_difficulty[priority]

    @property
    def initial_sync(self) -> bool:
        return len(self._task_cache) == 0

    @property
    def todoist_user_id(self) -> str | None:
        return self._todoist_user_id

    def _next_tasks_state(self) -> None:
        for todoist_task in self._todoist.state.items.values():  # pylint: disable=no-member
            generic_task = self._task_cache.get_task_by_todoist_task_id(todoist_task)

            if not generic_task:
                generic_task = GenericTask.from_todoist_task(todoist_task, StateTodoistNew.name())
                self._log.info(f"New task {generic_task.content}, {generic_task.state}")

            state = FSMState.factory(self, generic_task, todoist_task)

            try:
                state.next_state()
            except OSError as ex:
                self._log.error(f"Unexpected network error when processing task '{generic_task.content}': {str(ex)}")

        for generic_task in self._task_cache.dirty_habitica_tasks():
            try:
                state = FSMState.factory(self, generic_task)
                state.next_state()
            except OSError as ex:
                self._log.error(f"Unexpected network error when processing task '{generic_task.content}': {str(ex)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s (%(name)s) [%(levelname)s]: %(message)s")

    TasksSync().run_forever()
