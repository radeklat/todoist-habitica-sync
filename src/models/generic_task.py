from dataclasses import dataclass
from typing import Self

from models.todoist import TodoistPriority, TodoistTask


@dataclass
class GenericTask:
    todoist_task_id: str
    content: str
    priority: int
    state: str
    is_recurring: bool
    due_date_utc_timestamp: int | None
    habitica_task_id: str | None = None
    completed_at: str | None = None

    @classmethod
    def from_todoist_task(cls, todoist_task: TodoistTask, state: str) -> Self:
        return cls(
            todoist_task_id=todoist_task.id,
            content=todoist_task.content,
            priority=todoist_task.priority,
            state=state,
            due_date_utc_timestamp=todoist_task.due_date_utc_timestamp,
            is_recurring=bool(todoist_task.due and todoist_task.due.is_recurring),
        )

    def get_habitica_task_id(self) -> str:
        if self.habitica_task_id is None:
            raise RuntimeError("Habitica task ID is not set")
        return self.habitica_task_id

    @property
    def priority_enum(self) -> TodoistPriority:
        return TodoistPriority(self.priority)
