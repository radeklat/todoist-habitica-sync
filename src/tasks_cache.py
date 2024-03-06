import logging
from collections.abc import Iterator
from dataclasses import asdict
from typing import cast

from tinydb import Query, TinyDB, where

from config import get_settings
from models.generic_task import GenericTask
from models.todoist import TodoistTask


class TasksCache:
    """Tasks cache on disk.

    TinyDB docs: https://tinydb.readthedocs.io/en/latest/usage.html
    """

    def __init__(self, habitica_dirty_states: set[str]):
        db_file = get_settings().database_file
        db_file.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
        tiny_db = TinyDB(get_settings().database_file.resolve())  # pylint: disable=no-member
        self._habitica_dirty_states = frozenset(habitica_dirty_states)
        self._task_cache = tiny_db.table("tasks_cache")
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info(f"Tasks cache in {db_file.absolute()}")  # pylint: disable=no-member

    def __len__(self) -> int:
        return len(self._task_cache)

    def get_task_by_todoist_task_id(self, todoist_task: TodoistTask) -> GenericTask | None:
        task = self._task_cache.get(where("todoist_task_id") == todoist_task.id)
        if isinstance(task, list):
            self._log.warning(f"Found multiple tasks with todoist_task_id={todoist_task.id}. Using the first one.")
            task = task[0]

        return GenericTask(**task) if task else None

    def save_task(self, generic_task: GenericTask, previous_habitica_id: str | None = "") -> None:
        if previous_habitica_id != "":
            habitica_id = previous_habitica_id
        else:
            habitica_id = generic_task.habitica_task_id

        self._task_cache.upsert(
            asdict(generic_task),
            (where("todoist_task_id") == generic_task.todoist_task_id) & (where("habitica_task_id") == habitica_id),
        )

    def dirty_habitica_tasks(self) -> Iterator[GenericTask]:
        condition = Query().state.one_of(self._habitica_dirty_states)

        while task := cast(dict, self._task_cache.get(condition)):
            yield GenericTask(**task)
