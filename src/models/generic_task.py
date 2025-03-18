from dataclasses import dataclass

from models.todoist import TodoistPriority


@dataclass
class GenericTask:
    content: str
    priority: int
    state: str
    labels: list[str]
    habitica_task_id: str | None = None

    def get_habitica_task_id(self) -> str:
        if self.habitica_task_id is None:
            raise RuntimeError("Habitica task ID is not set")
        return self.habitica_task_id

    @property
    def priority_enum(self) -> TodoistPriority:
        return TodoistPriority(self.priority)
