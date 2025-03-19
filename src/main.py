from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Final

from pydantic import BaseModel, ConfigDict
from requests import HTTPError

from config import Settings, get_settings
from delay import DelayTimer
from habitica_api import HabiticaAPI, HabiticaAPIHeaders
from models.generic_task import GenericTask
from models.habitica import HabiticaDifficulty
from models.todoist import TodoistPriority
from tasks_cache import TasksCache
from todoist_api import TodoistAPI

_LOGGER = logging.getLogger(__name__)


class FSMState(BaseModel):
    context: TasksSync
    generic_task: GenericTask

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

    @classmethod
    def register(cls, state_cls: type[FSMState]) -> None:
        cls._STATES[state_cls.name()] = state_cls

    @classmethod
    def factory(cls, context: TasksSync, generic_task: GenericTask) -> FSMState:
        return cls._STATES[generic_task.state](context=context, generic_task=generic_task)


class StateHabiticaNew(FSMState):
    def next_state(self) -> None:
        self.generic_task.habitica_task_id = self.context.habitica.create_task(
            self.generic_task.content, self.generic_task.difficulty
        )["id"]
        self._set_state(StateHabiticaCreated)


class StateHabiticaCreated(FSMState):
    def next_state(self) -> None:
        try:
            self.context.habitica.score_task(self.generic_task.get_habitica_task_id())
            next_state: type[FSMState] = StateHabiticaFinished
        except HTTPError as ex:
            if ex.response is not None and ex.response.status_code == HTTPStatus.NOT_FOUND:
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
            if ex.response is not None and ex.response.status_code == HTTPStatus.NOT_FOUND:
                _LOGGER.warning(f"Habitica task '{self.generic_task.content}' not found.")
            else:
                raise ex

        self.context.delete_state(self.generic_task)


FSMState.register(StateHabiticaNew)
FSMState.register(StateHabiticaCreated)
FSMState.register(StateHabiticaFinished)


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

        self._task_cache = TasksCache()
        self._todoist = TodoistAPI(settings.todoist_api_key, self._task_cache.last_sync_datetime_utc)
        self._todoist_user_id = settings.todoist_user_id

        self._sync_sleep: Final[DelayTimer] = DelayTimer(
            settings.sync_delay_seconds, "Next check in {delay:.0f} seconds."
        )

    def run_forever(self) -> None:
        while True:
            try:
                self._task_cache.last_sync_datetime_utc = self._todoist.sync()
                self._next_tasks_state()
            except OSError as ex:
                self._log.error(f"Unexpected network error: {ex}")

            try:
                self._sync_sleep()
            except KeyboardInterrupt:
                break

    def set_state(self, state: FSMState) -> None:
        if state.generic_task.state != (new_state := state.name()):
            self._log.info(f"'{state.generic_task.content}' {state.generic_task.state} -> {new_state}")
            state.generic_task.state = new_state
            self._task_cache.save_task(state.generic_task)

    def delete_state(self, generic_task: GenericTask) -> None:
        self._log.info(f"'{generic_task.content}' done.")
        self._task_cache.delete_task(generic_task)

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
    def todoist_user_id(self) -> str | None:
        return self._todoist_user_id

    def _next_tasks_state(self) -> None:
        for todoist_completed_task in self._todoist.iter_pop_newly_completed_tasks():  # pylint: disable=no-member
            generic_task = GenericTask(
                content=todoist_completed_task.item_object.content,
                difficulty=self._get_task_difficulty(
                    get_settings(),
                    todoist_completed_task.item_object.labels,
                    TodoistPriority(todoist_completed_task.item_object.priority),
                ),
                state=StateHabiticaNew.name(),
            )
            self._task_cache.save_task(generic_task)
            self._log.info(f"'{generic_task.content}' -> {generic_task.state}")

        for generic_task in self._task_cache.in_progress_tasks():
            try:
                state = FSMState.factory(self, generic_task)
                state.next_state()
            except OSError as ex:
                self._log.error(f"Unexpected network error when processing task '{generic_task.content}': {str(ex)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s (%(name)s) [%(levelname)s]: %(message)s")

    TasksSync().run_forever()
