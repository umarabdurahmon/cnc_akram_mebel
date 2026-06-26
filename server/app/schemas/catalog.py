from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: int
    is_active: bool
    created_at: datetime


class StageCreate(BaseModel):
    name: str
    position: int | None = None


class StagePatch(BaseModel):
    name: str | None = None
    position: int | None = None
    is_active: bool | None = None
