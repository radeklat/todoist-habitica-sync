from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pydantic import BaseSettings, Field, validator


def positive_int(value: Any) -> int:
    result = int(value)

    if result <= 0:
        raise ValueError(f"Invalid value for positive int '{value}'. Must be >= 1.")

    return result


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    todoist_api_key: str = Field(..., description='See https://todoist.com/prefs/integrations under "API token".')
    todoist_user_id: int = Field(..., description='See "user_id" mentioned in a link under "Calendar Subscription URL" at https://todoist.com/prefs/integrations')
    habitica_user_id: str = Field(..., description='See https://habitica.com/user/settings/api under "User ID".')
    habitica_api_key: str = Field(..., description='See https://habitica.com/user/settings/api under "API Token", the "Show API Token" button.')
    sync_delay_seconds: int = Field(1, gt=0, env="sync_delay_minutes", description="Repeat sync automatically after N minutes.")
    database_file: Path = Field(Path(".sync_cache/sync_cache.json"), description="Where to store synchronisation details. No need to change.")

    @validator("sync_delay_seconds")
    def minutes_to_seconds(cls, value: int):  # pylint: disable=no-self-argument,no-self-use
        return value * 60


@lru_cache(maxsize=1)
def get_settings():
    return Settings()


# https://habitica.com/apidoc/#api-Task-CreateUserTasks
# https://developer.todoist.com/sync/v7/?python#items
TODOIST_PRIORITY_TO_HABITICA_DIFFICULTY = MappingProxyType({1: 0.1, 2: 1, 3: 2, 4: 1.5})

HABITICA_REQUEST_WAIT_TIME = 0.5  # time to pause between concurrent requests
