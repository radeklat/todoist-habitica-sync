import logging
from collections.abc import Iterator
from dataclasses import asdict
from typing import cast

from tinydb import Query, TinyDB, where

from config import get_settings
from models.generic_task import GenericTask


class TasksCache:
    """Tasks cache on disk.

    TinyDB docs: https://tinydb.readthedocs.io/en/latest/usage.html
    """

    def __init__(self, in_progress_states: set[str]):
        db_file = get_settings().database_file
        db_file.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
        tiny_db = TinyDB(get_settings().database_file.resolve())  # pylint: disable=no-member
        self._in_progress_states = frozenset(in_progress_states)
        self._task_cache = tiny_db.table("tasks_cache")
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info(f"Tasks cache in {db_file.absolute()}")  # pylint: disable=no-member

    def __len__(self) -> int:
        return len(self._task_cache)

    def save_task(self, generic_task: GenericTask, previous_habitica_id: str | None = "") -> None:
        if previous_habitica_id != "":
            habitica_id = previous_habitica_id
        else:
            habitica_id = generic_task.habitica_task_id

        self._task_cache.upsert(asdict(generic_task), where("habitica_task_id") == habitica_id)

    def delete_task(self, generic_task: GenericTask) -> None:
        self._task_cache.remove(where("habitica_task_id") == generic_task.habitica_task_id)

    def in_progress_tasks(self) -> Iterator[GenericTask]:
        condition = Query().state.one_of(self._in_progress_states)

        while task := cast(dict, self._task_cache.get(condition)):
            yield GenericTask(**task)
