from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from models.habitica import HabiticaDifficulty


class GenericTask(BaseModel):
    content: str
    difficulty: HabiticaDifficulty
    state: str
    habitica_task_id: str | None = None
    id: UUID = Field(default_factory=uuid4)

    def get_habitica_task_id(self) -> str:
        if self.habitica_task_id is None:
            raise RuntimeError("Habitica task ID is not set")
        return self.habitica_task_id
