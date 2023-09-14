import logging
from dataclasses import asdict
from typing import Iterator, Optional

from tinydb import Query, TinyDB, where

from config import get_settings
from models.generic_task import GenericTask, TaskState
from models.todoist import TodoistTask


class TasksCache:
    """Tasks cache on disk.

    TinyDB docs: https://tinydb.readthedocs.io/en/latest/usage.html
    """

    HABITICA_DIRTY_STATES = frozenset([TaskState.HABITICA_NEW, TaskState.HABITICA_CREATED, TaskState.HABITICA_FINISHED])

    def __init__(self):
        db_file = get_settings().database_file
        db_file.parent.mkdir(parents=True, exist_ok=True)
        tiny_db = TinyDB(get_settings().database_file.resolve())
        self._task_cache = tiny_db.table("tasks_cache")
        self._log = logging.getLogger(self.__class__.__name__)

    def __len__(self):
        return len(self._task_cache)

    def get_task_by_todoist_task_id(self, todoist_task: TodoistTask) -> Optional[GenericTask]:
        task = self._task_cache.get(where("todoist_task_id") == todoist_task.id)
        if isinstance(task, list):
            self._log.warning(f"Found multiple tasks with todoist_task_id={todoist_task.id}. Using the first one.")
            task = task[0]

        return GenericTask(**task) if task else None

    def set_task_state(self, generic_task: GenericTask, new_state: TaskState):
        if generic_task.state != new_state:
            self._log.info(f"'{generic_task.content}' {generic_task.state.name} -> {new_state.name}")
            generic_task.state = new_state
            self.save_task(generic_task)

    def set_habitica_id(self, generic_task: GenericTask, new_habitica_task_id: str):
        previous_habitica_id = generic_task.habitica_task_id
        generic_task.habitica_task_id = new_habitica_task_id
        self.save_task(generic_task, previous_habitica_id)

    def save_task(self, generic_task: GenericTask, previous_habitica_id: Optional[str] = ""):
        if previous_habitica_id != "":
            habitica_id = previous_habitica_id
        else:
            habitica_id = generic_task.habitica_task_id

        self._task_cache.upsert(
            asdict(generic_task),
            (where("todoist_task_id") == generic_task.todoist_task_id) & (where("habitica_task_id") == habitica_id),
        )

    def dirty_habitica_tasks(self) -> Iterator[GenericTask]:
        condition = Query().state.test(lambda _: _ in TasksCache.HABITICA_DIRTY_STATES)
        for task in self._task_cache.search(condition):
            yield GenericTask(**task)
