from enum import Enum


class HabiticaDifficulty(Enum):
    """See https://habitica.com/apidoc/#api-Task-CreateUserTasks."""

    TRIVIAL = 0.1
    EASY = 1
    MEDIUM = 1.5
    HARD = 2
