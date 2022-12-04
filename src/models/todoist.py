"""Models matching the v9 SYnc API.

See Also: https://developer.todoist.com/sync/v9/#read-resources
"""

from dateutil.parser import parse
from pydantic import BaseModel, Extra, Field, validator


class TodoistDue(BaseModel):
    date: str
    timezone: str | None
    string: str
    lang: str
    is_recurring: bool


class TodoistTask(BaseModel):
    checked: bool
    content: str
    due: TodoistDue | None
    id: str
    is_deleted: bool
    priority: int
    responsible_uid: str | None = None
    completed_at: str | None = None

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

    class Config:
        extra = Extra.allow


class TodoistState(BaseModel):
    sync_token: str
    full_sync: bool
    items: dict[str, TodoistTask] = Field(default_factory=dict)

    @validator("items", pre=True)
    def items_list_to_dict(cls, items: list[dict]) -> dict[str, dict]:  # pylint: disable=no-self-argument
        return {item["id"]: item for item in items}
