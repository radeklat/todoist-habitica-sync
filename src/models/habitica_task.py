from __future__ import annotations

import copy
from typing import NamedTuple, List, Dict


class HabiticaTask(NamedTuple):
    """https://habitica.com/apidoc/#api-Task-CreateUserTasks"""

    userId: str
    text: str
    type: str
    notes: str
    tags: List[str]
    value: str
    priority: str
    attribute: str
    challenge: str
    group: Dict
    reminders: List
    createdAt: str
    updatedAt: str
    checklist: List
    collapseChecklist: bool
    completed: bool
    id: str

    alias: str = ""

    @staticmethod
    def from_task_data(task_data: Dict) -> HabiticaTask:
        try:
            updated_task_data = copy.deepcopy(task_data)
            updated_task_data.pop("_id")

            return HabiticaTask(**updated_task_data)
        except TypeError as ex:
            raise TypeError(str(ex) + f"\nOffending task: {task_data}")
