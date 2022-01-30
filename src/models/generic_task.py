from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Optional

from models.todoist_task import TodoistTask


class TaskState(IntEnum):
    TODOIST_ACTIVE = auto()
    HABITICA_NEW = auto()
    HABITICA_CREATED = auto()
    HABITICA_FINISHED = auto()
    HIDDEN = auto()


@dataclass
class GenericTask:
    todoist_task_id: int
    content: str
    priority: int
    state: TaskState
    is_recurring: bool
    due_date_utc_timestamp: Optional[int]
    habitica_task_id: Optional[str] = None

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
            is_recurring=bool(todoist_task.due and todoist_task.due["is_recurring"]),
        )
