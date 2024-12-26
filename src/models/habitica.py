from enum import Enum


class HabiticaDifficulty(Enum):
    """See https://habitica.com/apidoc/#api-Task-CreateUserTasks."""

    TRIVIAL = "0.1"
    EASY = "1"
    MEDIUM = "1.5"
    HARD = "2"

    def __lt__(self, other):
        """To be able to use `min` and `max` on this enum."""
        if isinstance(other, HabiticaDifficulty):
            return float(self.value) < float(other.value)
        return NotImplemented
