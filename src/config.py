import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def positive_int(value: Any) -> int:
    result = int(value)

    if result <= 0:
        raise ValueError(f"Invalid value for positive int '{value}'. Must be >= 1.")

    return result


@dataclass(frozen=True)
class Config:
    todoist_api_key: str = os.environ["TODOIST_API_KEY"]
    habitica_user_id = os.environ["HABITICA_USER_ID"]
    habitica_api_key: str = os.environ["HABITICA_API_KEY"]
    sync_delay_seconds: int = positive_int(os.environ["SYNC_DELAY_MINUTES"]) * 60
    database_file: str = os.environ["DATABASE_FILE"]


# https://habitica.com/apidoc/#api-Task-CreateUserTasks
# https://developer.todoist.com/sync/v7/?python#items
TODOIST_PRIORITY_TO_HABITICA_DIFFICULTY = MappingProxyType({1: 0.1, 2: 1, 3: 2, 4: 1.5})

HABITICA_REQUEST_WAIT_TIME = 0.5  # time to pause between concurrent requests
