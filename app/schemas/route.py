from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.common import ORMModel, TimestampedResponse
from app.schemas.station import StationSummary


class RouteBase(ORMModel):
    origin_station_id: int
    destination_station_id: int
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    operator_name: str | None = Field(default=None, max_length=255)
    distance_km: Decimal | None = None
    is_active: bool = True


class RouteCreate(RouteBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_station_id": 1,
                "destination_station_id": 2,
                "name": "London Paddington to Bristol Temple Meads",
                "code": "PAD-BRI",
                "operator_name": "Great Western Railway",
                "distance_km": 189.5,
                "is_active": True,
            }
        }
    )


class RouteUpdate(ORMModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "operator_name": "Great Western Railway",
                "is_active": False,
            }
        }
    )

    origin_station_id: int | None = None
    destination_station_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    operator_name: str | None = Field(default=None, max_length=255)
    distance_km: Decimal | None = None
    is_active: bool | None = None


class RouteRead(TimestampedResponse, RouteBase):
    origin_station: StationSummary | None = None
    destination_station: StationSummary | None = None
