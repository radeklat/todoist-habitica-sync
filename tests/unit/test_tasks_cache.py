import itertools

from config import get_settings
from models.generic_task import GenericTask
from models.habitica import HabiticaDifficulty
from tasks_cache import TasksCache


def _task(content):
    return GenericTask(content=content, difficulty=HabiticaDifficulty.MEDIUM, state="New")


class TestInProgressTasks:
    @staticmethod
    def should_yield_each_cached_task_exactly_once(tmp_path, monkeypatch):
        monkeypatch.setenv("TODOIST_API_KEY", "test")
        monkeypatch.setenv("HABITICA_USER_ID", "test")
        monkeypatch.setenv("HABITICA_API_KEY", "test")
        monkeypatch.setenv("DATABASE_FILE", str(tmp_path / "cache.sqlite"))
        get_settings.cache_clear()
        try:
            cache = TasksCache()
            cache.save_task(_task("one"))
            cache.save_task(_task("two"))
            tasks = list(itertools.islice(cache.in_progress_tasks(), 5))
        finally:
            get_settings.cache_clear()
        assert sorted(task.content for task in tasks) == ["one", "two"]
