from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto

from models.todoist import TodoistTask


class TaskState(IntEnum):
    TODOIST_ACTIVE = auto()
    HABITICA_NEW = auto()
    HABITICA_CREATED = auto()
    HABITICA_FINISHED = auto()
    HIDDEN = auto()


@dataclass
class GenericTask:
    todoist_task_id: str
    content: str
    priority: int
    state: TaskState
    is_recurring: bool
    due_date_utc_timestamp: int | None
    habitica_task_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.state, TaskState):
            self.state = TaskState(self.state)

    @staticmethod
    def from_todoist_task(todoist_task: TodoistTask, task_state: TaskState) -> GenericTask:
        return GenericTask(
            todoist_task_id=todoist_task.id,
            content=todoist_task.content,
            priority=todoist_task.priority,
            state=task_state,
            due_date_utc_timestamp=todoist_task.due_date_utc_timestamp,
            is_recurring=bool(
                todoist_task.due and todoist_task.due.is_recurring),
        )
