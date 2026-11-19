from datetime import time
from functools import lru_cache
from pathlib import Path
from typing import Any

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


def parse_hh_mm(value: str) -> time:
    """Parse "HH:MM" (or "H:MM") into a time."""
    try:
        hours, minutes = (int(part) for part in value.strip().split(":"))
        return time(hours, minutes)
    except (TypeError, ValueError) as ex:
        raise ValueError(f"Expected a time as HH:MM, got {value!r}.") from ex


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8")

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
        Path(".sync_cache/sync_cache.sqlite"),
        description="Where to store synchronisation details. No need to change.",
    )
    priority_to_difficulty: dict[TodoistPriority, HabiticaDifficulty] = Field(
        # The default is formed of the enum names for better documentation
        {key.name: value.name for key, value in _DEFAULT_PRIORITY_TO_DIFFICULTY.items()},  # type: ignore[misc]
        description=(
            "Defines how Todoist priorities map to Habitica difficulties. Keys/values are case-insensitive "
            "and can be both names or numerical values defines by the APIs. "
            "See https://habitica.com/apidoc/#api-Task-CreateUserTasks and "
            "https://developer.todoist.com/api/v1/ (task `priority`: 4 is p1, 1 is p4) for numerical values "
            "definitions."
        ),
    )
    label_to_difficulty: dict[str, HabiticaDifficulty] = Field(
        default_factory=dict,
        description=(
            "Defines how Todoist labels map to Habitica difficulties. Keys are case-insensitive. "
            "See https://habitica.com/apidoc/#api-Task-CreateUserTasks for difficulty values. If a task "
            "has no matching label, the `priority_to_difficulty` mapping is used. If a task has multiple "
            "labels, the highest difficulty is used."
        ),
    )
    nightly_penalty_enabled: bool = Field(
        False,
        description=(
            "Once a night, tap a negative Habitica habit for each overdue Todoist task assigned to you or to no one. "
            "Costs HP, so it is off by default."
        ),
    )
    penalty_time: str = Field(
        "00:05",
        description="Local time (HH:MM, in your Todoist timezone) to run the nightly penalty.",
    )
    penalty_window_hours: float = Field(
        4,
        ge=0,
        description=(
            "If the nightly penalty could not run within this many hours after `PENALTY_TIME` "
            "(e.g. the server was off), that night is skipped. It never charges late."
        ),
    )
    penalty_max_per_night: int = Field(5, ge=0, description="Most habit taps per night.")
    penalty_habit_name: str = Field(
        "Unaccounted task",
        description="The Habitica habit to tap for the nightly penalty. It is created if missing.",
    )
    penalty_exclude_labels: str = Field(
        "Exclude,no_penalty",
        description=(
            "Comma-separated Todoist labels (case-insensitive) whose tasks never count for the nightly penalty."
        ),
    )
    penalty_pause_label: str = Field(
        "pause_penalties",
        description=(
            "If any active Todoist task has this label (case-insensitive), the nightly penalty skips the night."
        ),
    )

    @field_validator("penalty_time")
    @classmethod
    def validate_penalty_time(cls, value: str) -> str:
        parse_hh_mm(value)
        return value

    @property
    def penalty_run_at(self) -> time:
        return parse_hh_mm(self.penalty_time)

    @property
    def penalty_exclude_label_set(self) -> set[str]:
        return {label.strip().lower() for label in self.penalty_exclude_labels.split(",") if label.strip()}

    @field_validator("sync_delay_seconds")
    @classmethod
    def minutes_to_seconds(cls, value: int):  # pylint: disable=no-self-argument
        return value * 60

    @field_validator("priority_to_difficulty", mode="before")
    @classmethod
    def transform_enum_names_to_values(
        cls,
        priority_to_difficulty: dict[str | int | float | TodoistPriority, str | HabiticaDifficulty],
    ) -> dict[TodoistPriority | str, HabiticaDifficulty | float | int]:
        output: dict[Any, Any] = {}  # disable type checking for the dict values as it gets it wrong and tests cover it

        for priority, difficulty in priority_to_difficulty.items():
            new_priority = priority
            new_difficulty = difficulty

            if isinstance(priority, str):
                try:
                    new_priority = int(priority)
                except ValueError:
                    # If it's not a number, it could be an enum name
                    new_priority = TodoistPriority[priority.upper()]

            if isinstance(difficulty, str):
                try:
                    float(difficulty)  # If it's a number, it's an enum value
                except ValueError:  # If it's not a number, it's an enum name
                    new_difficulty = HabiticaDifficulty[difficulty.upper()]

            if isinstance(difficulty, (float, int)):  # If it's a number, it's an enum value
                new_difficulty = str(difficulty)

            output[new_priority] = new_difficulty

        return output

    @field_validator("priority_to_difficulty")
    @classmethod
    def validate_priority_to_difficulty(cls, value: dict[TodoistPriority, HabiticaDifficulty]):
        # The dict must have all keys from TodoistPriority
        if missing_keys := ", ".join(sorted(_.name for _ in set(TodoistPriority) - set(value.keys()))):
            raise ValueError(
                f"priority_to_difficulty must have all priority levels defined, but missing: {missing_keys}"
            )
        return value

    @field_validator("label_to_difficulty", mode="before")
    @classmethod
    def transform_label_to_difficulty(
        cls, label_to_difficulty: dict[str, str | HabiticaDifficulty]
    ) -> dict[str, HabiticaDifficulty]:
        return {
            label.lower(): (HabiticaDifficulty[difficulty.upper()] if isinstance(difficulty, str) else difficulty)
            for label, difficulty in label_to_difficulty.items()
        }


@lru_cache(maxsize=1)
def get_settings():
    # We don't want to read the environment variables in the tests
    Settings.model_config["env_file"] = ".env"

    return Settings()
