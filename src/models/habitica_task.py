from __future__ import annotations

import copy
from typing import Dict

from pydantic import BaseModel


class HabiticaTask(BaseModel):
    """Single Habitica task.

    See:
        https://habitica.com/apidoc/#api-Task-CreateUserTasks
    """

    id: str
    text: str

    @staticmethod
    def from_task_data(task_data: Dict) -> HabiticaTask:
        try:
            updated_task_data = copy.deepcopy(task_data)
            updated_task_data.pop("_id")

            return HabiticaTask(**updated_task_data)
        except TypeError as ex:
            raise TypeError(str(ex) + f"\nOffending task: {task_data}") from ex
