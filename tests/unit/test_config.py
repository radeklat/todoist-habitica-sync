import pytest

from config import _DEFAULT_PRIORITY_TO_DIFFICULTY, Settings, get_settings
from models.habitica import HabiticaDifficulty
from models.todoist import TodoistPriority


class TestConfigPriorityToDifficulty:
    @staticmethod
    def should_refuse_incomplete_mapping():
        with pytest.raises(ValueError) as exc_info:
            Settings(priority_to_difficulty={TodoistPriority.P1: HabiticaDifficulty.HARD})

        exception_text = str(exc_info.value)

        assert "must have all priority levels defined" in exception_text
        assert "missing: P2, P3, P4" in exception_text

    @staticmethod
    def should_accept_keys_as_enum_names():
        settings = Settings(
            priority_to_difficulty={
                "p1": "hard",
                "p2": "medium",
                "p3": "easy",
                "p4": "trivial",
            }
        )
        assert settings.priority_to_difficulty == _DEFAULT_PRIORITY_TO_DIFFICULTY

    @staticmethod
    def should_ignore_casing():
        settings = Settings(
            priority_to_difficulty={
                "P1": "Hard",
                "p2": "Medium",
                "P3": "Easy",
                "P4": "Trivial",
            }
        )
        assert settings.priority_to_difficulty == _DEFAULT_PRIORITY_TO_DIFFICULTY

    @staticmethod
    def should_accept_keys_as_enum_values():
        settings = Settings(priority_to_difficulty={4: 2, 3: 1.5, 2: 1, 1: 0.1})
        assert settings.priority_to_difficulty == _DEFAULT_PRIORITY_TO_DIFFICULTY

    @staticmethod
    def should_have_default_values():
        assert Settings().priority_to_difficulty == _DEFAULT_PRIORITY_TO_DIFFICULTY


class TestConfigLabelToDifficulty:
    @staticmethod
    def should_accept_label_to_difficulty():
        settings = Settings(
            label_to_difficulty={
                "urgent": "hard",
                "important": "medium",
                "normal": "easy",
                "low": "trivial",
            }
        )
        assert settings.label_to_difficulty == {
            "urgent": HabiticaDifficulty.HARD,
            "important": HabiticaDifficulty.MEDIUM,
            "normal": HabiticaDifficulty.EASY,
            "low": HabiticaDifficulty.TRIVIAL,
        }

    @staticmethod
    def should_ignore_casing_in_label_to_difficulty():
        settings = Settings(
            label_to_difficulty={
                "Urgent": "Hard",
                "IMPORTANT": "Medium",
                "Normal": "Easy",
                "low": "Trivial",
            }
        )
        assert settings.label_to_difficulty == {
            "urgent": HabiticaDifficulty.HARD,
            "important": HabiticaDifficulty.MEDIUM,
            "normal": HabiticaDifficulty.EASY,
            "low": HabiticaDifficulty.TRIVIAL,
        }

    @staticmethod
    def should_have_default_empty_label_to_difficulty():
        assert Settings().label_to_difficulty == {}


class TestGetSettings:
    @staticmethod
    def should_cache_settings():
        assert get_settings() is get_settings()
