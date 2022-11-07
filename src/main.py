import logging
import time

from os.path import dirname, join
from typing import Final

from requests import HTTPError

from config import TODOIST_PRIORITY_TO_HABITICA_DIFFICULTY, get_settings
from delay import DelayTimer
from habitica_api import HabiticaAPI, HabiticaAPIHeaders
from models.generic_task import GenericTask, TaskState
from models.habitica_task import HabiticaTask
from models.todoist import TodoistTask
from tasks_cache import TasksCache
from todoist_api import TodoistAPI


class TasksSync:  # pylint: disable=too-few-public-methods
    """Class managing tasks synchronisation.

    Todoist API: https://developer.todoist.com/sync/v7/?python#overview
    Habitica API: https://habitica.com/apidoc
    """

    TODOIST_CONTINUE_STATES = frozenset(
        [TaskState.HIDDEN, *TasksCache.HABITICA_DIRTY_STATES])

    def __init__(self):
        settings = get_settings()

        self._habitica = HabiticaAPI(
            HabiticaAPIHeaders(user_id=settings.habitica_user_id,
                               api_key=settings.habitica_api_key)
        )

        self._log = logging.getLogger(self.__class__.__name__)
        self._todoist = TodoistAPI(settings.todoist_api_key)
        self._todoist_user_id = settings.todoist_user_id

        self._task_cache = TasksCache()
        self._sync_sleep: Final[DelayTimer] = DelayTimer(
            settings.sync_delay_seconds, "Next check in {delay:.0f} seconds."
        )

    def run_forever(self):
        timeout = time.time() + 60*10
        while True:
            try:
                self._todoist.sync()
                self._next_tasks_state_based_on_todoist()
                self._next_tasks_state_in_habitica()
            except IOError as ex:
                self._log.error(f"Unexpected network error: {ex}")

            try:
                if(time.time() < timeout):
                    self._sync_sleep()
                else:
                    break
            except KeyboardInterrupt:
                break

    def _next_state_with_existing_generic_task(self, todoist_task: TodoistTask, generic_task: GenericTask) -> TaskState:
        if todoist_task.is_deleted:
            return TaskState.HIDDEN

        if self._should_task_score_points(todoist_task, generic_task):
            return TaskState.HABITICA_NEW if self._owned_by_me(todoist_task) else TaskState.HIDDEN

        return TaskState.TODOIST_ACTIVE

    def _next_state_with_new_generic_task(self, todoist_task: TodoistTask, initial_sync: bool) -> TaskState:
        if todoist_task.is_deleted:
            return TaskState.HIDDEN

        if not todoist_task.checked:
            return TaskState.TODOIST_ACTIVE

        if initial_sync:
            return TaskState.HIDDEN

        if self._should_task_score_points(todoist_task):
            return TaskState.HABITICA_NEW if self._owned_by_me(todoist_task) else TaskState.HIDDEN

        return TaskState.TODOIST_ACTIVE

    def _next_tasks_state_based_on_todoist(self):
        initial_sync = len(self._task_cache) == 0

        for todoist_task in self._todoist.state.items.values():
            generic_task = self._task_cache.get_task_by_todoist_task_id(
                todoist_task)

            if generic_task:
                if generic_task.state in self.TODOIST_CONTINUE_STATES:
                    continue

                self._task_cache.set_task_state(
                    generic_task, self._next_state_with_existing_generic_task(
                        todoist_task, generic_task)
                )
                generic_task.content = todoist_task.content
                generic_task.priority = todoist_task.priority
            else:
                generic_task = GenericTask.from_todoist_task(
                    todoist_task,
                    self._next_state_with_new_generic_task(
                        todoist_task, initial_sync),
                )
                self._log.info(
                    f"New task {generic_task.content}, {generic_task.state.name}")

            self._task_cache.save_task(generic_task)

    @staticmethod
    def _should_task_score_points(todoist_task: TodoistTask, generic_task: GenericTask = None) -> bool:
        if todoist_task.checked:
            return True

        if generic_task:
            recurring_task_checked = bool(
                todoist_task.due is not None
                and todoist_task.due.is_recurring
                and generic_task.due_date_utc_timestamp
                and todoist_task.due_date_utc_timestamp
                and generic_task.due_date_utc_timestamp < todoist_task.due_date_utc_timestamp
            )

            if recurring_task_checked:
                generic_task.due_date_utc_timestamp = todoist_task.due_date_utc_timestamp
                return True

        return False

    def _owned_by_me(self, todoist_task: TodoistTask) -> bool:
        if self._todoist_user_id is None or todoist_task.responsible_uid is None:
            return True
        return todoist_task.responsible_uid == self._todoist_user_id

    # TODO: Improve FSM algorithm
    def _next_tasks_state_in_habitica(self):  # pylint: disable=too-complex
        for generic_task in self._task_cache.dirty_habitica_tasks():
            try:
                if generic_task.state == TaskState.HABITICA_NEW:
                    habitica_task = HabiticaTask.from_task_data(
                        self._habitica.user.tasks(
                            type="todo",
                            text=generic_task.content,
                            priority=TODOIST_PRIORITY_TO_HABITICA_DIFFICULTY[generic_task.priority],
                            _method="post",
                        )
                    )
                    self._task_cache.set_habitica_id(
                        generic_task, habitica_task.id)
                    self._task_cache.set_task_state(
                        generic_task, TaskState.HABITICA_CREATED)

                if generic_task.state == TaskState.HABITICA_CREATED:
                    try:
                        self._habitica.user.tasks(
                            _id=generic_task.habitica_task_id,
                            _direction="up",
                            _method="post",
                        )
                        next_state = TaskState.HABITICA_FINISHED
                    except HTTPError as ex:
                        if ex.response.status_code == 404:
                            next_state = TaskState.HABITICA_NEW
                            self._log.warning(
                                f"Habitica task '{generic_task.content}' not found. " f"Re-setting state."
                            )
                        else:
                            raise ex

                    self._task_cache.set_task_state(generic_task, next_state)

                if generic_task.state == TaskState.HABITICA_FINISHED:
                    try:
                        self._habitica.user.tasks(
                            _id=generic_task.habitica_task_id, _method="delete")
                    except HTTPError as ex:
                        if ex.response.status_code == 404:
                            self._log.warning(
                                f"Habitica task '{generic_task.content}' not found.")
                        else:
                            raise ex

                    next_state = TaskState.TODOIST_ACTIVE if generic_task.is_recurring else TaskState.HIDDEN
                    self._task_cache.set_task_state(generic_task, next_state)
            except IOError as ex:
                self._log.error(f"Unexpected network error: {str(ex)}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s (%(name)s) [%(levelname)s]: %(message)s")

    TasksSync().run_forever()
