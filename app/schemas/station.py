from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedResponse


class StationBase(ORMModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class StationCreate(StationBase):
    pass


class StationUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class StationSummary(ORMModel):
    id: int
    name: str
    code: str | None
    city: str | None


class StationRead(TimestampedResponse, StationBase):
    pass
