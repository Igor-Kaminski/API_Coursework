from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.common import ORMModel, TimestampedResponse


class StationBase(ORMModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    crs_code: str | None = Field(default=None, max_length=3)
    tiploc_code: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class StationCreate(StationBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "London Paddington",
                "code": "PAD",
                "crs_code": "PAD",
                "tiploc_code": "PADTON",
                "city": "London",
                "latitude": 51.5154,
                "longitude": -0.1755,
            }
        }
    )


class StationUpdate(ORMModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "London",
                "latitude": 51.5154,
                "longitude": -0.1755,
            }
        }
    )

    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    crs_code: str | None = Field(default=None, max_length=3)
    tiploc_code: str | None = Field(default=None, max_length=32)
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
