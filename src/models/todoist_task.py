from __future__ import annotations

import copy
from typing import Any, Dict, List, NamedTuple, Optional

from dateutil.parser import parse


class TodoistTask(NamedTuple):
    assigned_by_uid: int
    checked: int
    child_order: int
    collapsed: int
    content: str
    date_added: str
    date_completed: str
    day_order: int
    due: Dict[str, Any]  # date, is_recurring, lang, string, timezone
    id: int
    in_history: int
    is_deleted: int
    labels: List[str]
    parent_id: Optional[int]
    priority: int
    project_id: int
    responsible_uid: Optional[int]
    section_id: Optional[int]
    sync_id: Optional[int]
    user_id: int

    # Optional values
    has_more_notes: bool = False
    legacy_id: Optional[int] = None
    legacy_project_id: Optional[int] = None
    legacy_parent_id: Optional[int] = None

    # custom fields with default value
    due_date_utc_timestamp: Optional[int] = None

    @staticmethod
    def from_task_data(task_data: Dict) -> TodoistTask:
        try:
            updated_task_data = copy.deepcopy(task_data)
            due = updated_task_data["due"]

            if due is not None:
                updated_task_data["due_date_utc_timestamp"] = int(
                    parse(due["date"]).timestamp()
                )

            return TodoistTask(**updated_task_data)
        except (KeyError, TypeError) as ex:
            raise ex.__class__(str(ex) + f"\nOffending task: {task_data}") from ex
