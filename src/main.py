import logging
import time
from os.path import dirname, join

import todoist
from requests import HTTPError

from config import HABITICA_REQUEST_WAIT_TIME, TODOIST_PRIORITY_TO_HABITICA_DIFFICULTY, get_settings
from habitica_api import HabiticaAPI
from models.generic_task import GenericTask, TaskState
from models.habitica_task import HabiticaTask
from models.todoist_task import TodoistTask
from tasks_cache import TasksCache


class TasksSync:  # pylint: disable=too-few-public-methods
    """Class managing tasks synchronisation.

    Todoist API: https://developer.todoist.com/sync/v7/?python#overview
    Habitica API: https://habitica.com/apidoc
    """

    TODOIST_CONTINUE_STATES = frozenset([TaskState.HIDDEN, *TasksCache.HABITICA_DIRTY_STATES])

    def __init__(self):
        self._habitica = HabiticaAPI(
            {
                "url": "https://habitica.com",
                "x-api-user": get_settings().habitica_user_id,
                "x-api-key": get_settings().habitica_api_key,
            }
        )

        self._log = logging.getLogger(self.__class__.__name__)
        self._todoist = todoist.TodoistAPI(
            get_settings().todoist_api_key, cache=join(dirname(__file__), ".todoist-sync/")
        )

        self._task_cache = TasksCache()

    def run_forever(self):
        while True:
            start_time = time.time()

            try:
                self._sync_todoist()
                self._next_tasks_state_based_on_todoist()
                self._next_tasks_state_in_habitica()
            except IOError as ex:
                self._log.error(f"Unexpected network error: {ex}")

            duration = time.time() - start_time
            delay = max(0.0, get_settings().sync_delay_seconds - duration)

            try:
                self._log.info(f"Next check in {delay:.0f} seconds.")
                time.sleep(delay)
            except KeyboardInterrupt:
                break

    def _sync_todoist(self):
        self._todoist.sync()

    def _next_state_with_existing_generic_task(self, todoist_task: TodoistTask, generic_task: GenericTask) -> TaskState:
        if todoist_task.is_deleted:
            return TaskState.HIDDEN

        if self._should_task_score_points(todoist_task, generic_task):
            return TaskState.HABITICA_NEW

        return TaskState.TODOIST_ACTIVE

    def _next_state_with_new_generic_task(self, todoist_task: TodoistTask, initial_sync: bool) -> TaskState:
        if todoist_task.is_deleted:
            return TaskState.HIDDEN

        if not todoist_task.checked:
            return TaskState.TODOIST_ACTIVE

        if initial_sync:
            return TaskState.HIDDEN

        if self._should_task_score_points(todoist_task):
            return TaskState.HABITICA_NEW

        return TaskState.TODOIST_ACTIVE

    def _next_tasks_state_based_on_todoist(self):
        initial_sync = len(self._task_cache) == 0

        for task in self._todoist.state["items"]:
            todoist_task = TodoistTask.from_task_data(task.data)
            generic_task = self._task_cache.get_task_by_todoist_task_id(todoist_task)

            if generic_task:
                if generic_task.state in self.TODOIST_CONTINUE_STATES:
                    continue

                generic_task.state = self._next_state_with_existing_generic_task(todoist_task, generic_task)
                generic_task.content = todoist_task.content
                generic_task.priority = todoist_task.priority
            else:
                generic_task = GenericTask.from_todoist_task(
                    todoist_task,
                    self._next_state_with_new_generic_task(todoist_task, initial_sync),
                )
                self._log.info(f"New task {generic_task.content}, {generic_task.state.name}")

            self._task_cache.save_task(generic_task)

    @staticmethod
    def _should_task_score_points(todoist_task: TodoistTask, generic_task: GenericTask = None) -> bool:
        if todoist_task.checked:
            return True

        if generic_task:
            recurring_task_checked = bool(
                todoist_task.due is not None
                and todoist_task.due["is_recurring"]
                and generic_task.due_date_utc_timestamp
                and todoist_task.due_date_utc_timestamp
                and generic_task.due_date_utc_timestamp < todoist_task.due_date_utc_timestamp
            )

            if recurring_task_checked:
                generic_task.due_date_utc_timestamp = todoist_task.due_date_utc_timestamp
                return True

        return False

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
                    self._task_cache.set_habitica_id(generic_task, habitica_task.id)
                    self._task_cache.set_task_state(generic_task, TaskState.HABITICA_CREATED)
                    time.sleep(HABITICA_REQUEST_WAIT_TIME)

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
                    time.sleep(HABITICA_REQUEST_WAIT_TIME)

                if generic_task.state == TaskState.HABITICA_FINISHED:
                    try:
                        self._habitica.user.tasks(_id=generic_task.habitica_task_id, _method="delete")
                    except HTTPError as ex:
                        if ex.response.status_code == 404:
                            self._log.warning(f"Habitica task '{generic_task.content}' not found.")
                        else:
                            raise ex

                    next_state = TaskState.TODOIST_ACTIVE if generic_task.is_recurring else TaskState.HIDDEN
                    self._task_cache.set_task_state(generic_task, next_state)
                    time.sleep(HABITICA_REQUEST_WAIT_TIME)
            except IOError as ex:
                self._log.error(f"Unexpected network error: {str(ex)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s (%(name)s) [%(levelname)s]: %(message)s")

    TasksSync().run_forever()
