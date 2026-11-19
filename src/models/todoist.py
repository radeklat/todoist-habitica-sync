"""Models for Todoist tasks.

`todoist_api.TodoistAPI` builds these from Todoist API v1 responses.

See Also: https://developer.todoist.com/api/v1/
"""

from enum import Enum

from dateutil.parser import parse
from pydantic import BaseModel, ConfigDict, Field


class TodoistPriority(Enum):
    P1 = 4
    P2 = 3
    P3 = 2
    P4 = 1


class TodoistDue(BaseModel):
    date: str
    timezone: str | None = None
    string: str
    lang: str
    is_recurring: bool


class TodoistTask(BaseModel):
    checked: bool
    content: str
    due: TodoistDue | None = None
    id: str
    is_deleted: bool
    priority: int
    responsible_uid: str | None = None
    completed_at: str | None = None
    labels: list[str] = Field(default_factory=list)

    # custom fields with default value
    due_date_utc_timestamp: int | None = None
    completed_at_utc_timestamp: int | None = None

    @property
    def latest_completion(self) -> int:
        return max(self.due_date_utc_timestamp or 0, self.completed_at_utc_timestamp or 0)

    @property
    def is_recurring(self) -> bool:
        return self.due is not None and self.due.is_recurring

    def __init__(self, **data):
        super().__init__(**data)
        if (due := data.get("due", None)) is not None:
            self.due_date_utc_timestamp = int(parse(due["date"]).timestamp())
        if (completed_at := data.get("completed_at", None)) is not None:
            self.completed_at_utc_timestamp = int(parse(completed_at).timestamp())

    model_config = ConfigDict(extra="allow")


class CompletedTodoistTask(BaseModel):
    task_id: str
    user_id: str
    completed_at: str
    item_object: TodoistTask
