from __future__ import annotations

import copy
import datetime
from typing import (
    NamedTuple,
    Optional,
    List,
    Dict,
)


_TIME_FORMAT = '%a %d %b %Y %H:%M:%S %z'


class TodoistTask(NamedTuple):
    all_day: bool
    assigned_by_uid: int
    checked: int
    collapsed: int
    content: str
    date_added: str
    date_completed: str
    date_lang: str
    date_string: Optional[str]
    day_order: int
    due_date_utc: Optional[str]
    id: int
    in_history: int
    indent: int
    is_archived: int
    is_deleted: int
    item_order: int
    labels: List[str]
    parent_id: int
    priority: int
    project_id: int
    responsible_uid: int
    sync_id: int
    user_id: int

    # custom fields without default value
    is_repeated: bool

    # custom fields with default value
    due_date_utc_timestamp: Optional[int] = None

    # standard fields with default value
    has_more_notes: bool = False

    @staticmethod
    def from_task_data(task_data: Dict) -> TodoistTask:
        try:
            updated_task_data = copy.deepcopy(task_data)

            if updated_task_data['due_date_utc'] is not None:
                updated_task_data['due_date_utc_timestamp'] = int(
                    datetime.datetime.strptime(
                        updated_task_data['due_date_utc'], _TIME_FORMAT
                    ).timestamp()
                )

            updated_task_data['is_repeated'] = (
                updated_task_data['date_string'] is not None
                and "every" in updated_task_data['date_string']
            )

            return TodoistTask(**updated_task_data)
        except TypeError as ex:
            raise TypeError(str(ex) + f"\nOffending task: {task_data}")
