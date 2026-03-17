from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StationBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=20)


class StationCreate(StationBase):
    pass


class StationUpdate(StationBase):
    pass


class StationRead(StationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
