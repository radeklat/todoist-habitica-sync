import json
import logging
import sqlite3
from collections.abc import Iterator
from collections.abc import Iterator as TypingIterator
from contextlib import contextmanager
from datetime import datetime, timezone

from config import get_settings
from models.generic_task import GenericTask

_DATABASE_SCHEMAS = [
    """
CREATE TABLE IF NOT EXISTS tasks_cache (
    id TEXT PRIMARY KEY NOT NULL,
    task_data TEXT
)
""",
    """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT
)
""",
]


class TasksCache:
    """Tasks cache on disk using SQLite."""

    def __init__(self):
        db_file = get_settings().database_file  # pylint: disable=no-member
        db_file.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
        self._db_path = str(db_file.resolve())  # pylint: disable=no-member
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info(f"Tasks cache in {db_file.absolute()}")  # pylint: disable=no-member

        self._initialize_database()

    @contextmanager
    def _cursor(self, row_factory=None) -> TypingIterator[sqlite3.Cursor]:
        """Context manager for database cursor operations."""
        conn = sqlite3.connect(self._db_path)
        if row_factory:
            conn.row_factory = row_factory
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        finally:
            conn.close()

    def _initialize_database(self) -> None:
        with self._cursor() as cursor:
            for database_schema in _DATABASE_SCHEMAS:
                cursor.execute(database_schema)

    def _read_metadata(self, key: str, default: str | None = None) -> str | None:
        with self._cursor() as cursor:
            cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
            return row[0] if (row := cursor.fetchone()) else default

    def _write_metadata(self, key: str, value: str) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (key, value),
            )

    @property
    def last_sync_datetime_utc(self) -> str | None:
        return self._read_metadata(
            "last_sync_datetime_utc",
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

    @last_sync_datetime_utc.setter
    def last_sync_datetime_utc(self, value: str) -> None:
        self._write_metadata("last_sync_datetime_utc", value)

    def save_task(self, generic_task: GenericTask) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO tasks_cache (id, task_data) VALUES (?, ?)",
                (str(generic_task.id), generic_task.model_dump_json()),
            )

    def delete_task(self, generic_task: GenericTask) -> None:
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM tasks_cache WHERE id = ?", (str(generic_task.id),))

    def in_progress_tasks(self) -> Iterator[GenericTask]:
        while True:
            with self._cursor(row_factory=sqlite3.Row) as cursor:
                cursor.execute("SELECT task_data FROM tasks_cache LIMIT 1")

                if not (row := cursor.fetchone()):
                    break

                yield GenericTask(**json.loads(row["task_data"]))
