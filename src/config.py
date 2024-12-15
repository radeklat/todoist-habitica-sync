from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from models.habitica import HabiticaDifficulty
from models.todoist import TodoistPriority

_DEFAULT_PRIORITY_TO_DIFFICULTY = {
    TodoistPriority.P1: HabiticaDifficulty.HARD,
    TodoistPriority.P2: HabiticaDifficulty.MEDIUM,
    TodoistPriority.P3: HabiticaDifficulty.EASY,
    TodoistPriority.P4: HabiticaDifficulty.TRIVIAL,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    todoist_user_id: int | None = Field(
        None,
        description=(
            'See "user_id" mentioned in a link under "Calendar Subscription URL" at '
            "https://todoist.com/prefs/integrations. Needed only for shared projects to "
            "score points for tasks owned by you."
        ),
    )
    todoist_api_key: str = Field(..., description='See https://todoist.com/prefs/integrations under "API token".')
    habitica_user_id: str = Field(..., description='See https://habitica.com/user/settings/api under "User ID".')
    habitica_api_key: str = Field(
        ...,
        description='See https://habitica.com/user/settings/api under "API Token", the "Show API Token" button.',
    )
    sync_delay_seconds: int = Field(
        1,
        gt=0,
        validation_alias="sync_delay_minutes",
        description="Repeat sync automatically after N minutes.",
    )
    database_file: Path = Field(
        Path(".sync_cache/sync_cache.json"),
        description="Where to store synchronisation details. No need to change.",
    )
    priority_to_difficulty: dict[TodoistPriority, HabiticaDifficulty] = Field(
        # The default is formed of the enum names for better documentation
        {key.name: value.name for key, value in _DEFAULT_PRIORITY_TO_DIFFICULTY.items()},  # type: ignore[misc]
        description=(
            "Defines how Todoist priorities map to Habitica difficulties. Keys/values are case-insensitive "
            "and can be both names or numerical values defines by the APIs. "
            "See https://habitica.com/apidoc/#api-Task-CreateUserTasks and "
            "https://developer.todoist.com/sync/v9/#items for numerical values definitions."
        ),
    )

    @field_validator("sync_delay_seconds")
    @classmethod
    def minutes_to_seconds(cls, value: int):  # pylint: disable=no-self-argument
        return value * 60

    @field_validator("priority_to_difficulty", mode="before")
    @classmethod
    def tranforms_enum_names_to_values(
        cls,
        priority_to_difficulty: dict[str | TodoistPriority, str | HabiticaDifficulty],
    ) -> dict[TodoistPriority, HabiticaDifficulty]:
        return {
            TodoistPriority[priority.upper()] if isinstance(priority, str) else priority: (
                HabiticaDifficulty[difficulty.upper()] if isinstance(difficulty, str) else difficulty
            )
            for priority, difficulty in priority_to_difficulty.items()
        }

    @field_validator("priority_to_difficulty")
    @classmethod
    def validate_priority_to_difficulty(cls, value: dict[TodoistPriority, HabiticaDifficulty]):
        # The dict must have all keys from TodoistPriority
        if missing_keys := ", ".join(sorted(_.name for _ in set(TodoistPriority) - set(value.keys()))):
            raise ValueError(
                f"priority_to_difficulty must have all priority levels defined, but missing: {missing_keys}"
            )
        return value


@lru_cache(maxsize=1)
def get_settings():
    return Settings()
