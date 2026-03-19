from decimal import Decimal

from pydantic import Field

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
    pass


class RouteUpdate(ORMModel):
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
