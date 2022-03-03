import copy
from typing import Any, Dict, Optional

from dateutil.parser import parse
from pydantic import BaseModel


class TodoistTask(BaseModel):
    checked: int
    content: str
    due: Optional[Dict[str, Any]]  # date, is_recurring, lang, string, timezone
    id: int
    user_id: Optional[int]
    is_deleted: int
    responsible_uid: Optional[int]
    priority: int
    legacy_id: Optional[int] = None

    # custom fields with default value
    due_date_utc_timestamp: Optional[int] = None

    @staticmethod
    def from_task_data(task_data: Dict) -> "TodoistTask":
        try:
            updated_task_data = copy.deepcopy(task_data)
            due = updated_task_data["due"]
            responsible_uid = updated_task_data["responsible_uid"]

            if responsible_uid is not None:
                updated_task_data["responsible_uid"] = int(responsible_uid)
            # else:
            #     updated_task_data["responsible_uid"] = -1

            if due is not None:
                updated_task_data["due_date_utc_timestamp"] = int(parse(due["date"]).timestamp())

            return TodoistTask(**updated_task_data)
        except (KeyError, TypeError) as ex:
            raise ex.__class__(str(ex) + f"\nOffending task: {task_data}") from ex
