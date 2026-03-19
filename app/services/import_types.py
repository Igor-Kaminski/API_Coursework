from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(slots=True)
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0


@dataclass(slots=True)
class StationImportRecord:
    name: str
    code: str | None = None
    tiploc_code: str | None = None
    crs_code: str | None = None
    city: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


@dataclass(slots=True)
class RouteImportRecord:
    origin_station_code: str
    destination_station_code: str
    name: str
    code: str | None = None
    operator_name: str | None = None
    distance_km: Decimal | None = None
    is_active: bool = True


@dataclass(slots=True)
class JourneyImportRecord:
    route_code: str | None
    origin_station_code: str
    destination_station_code: str
    route_name: str
    operator_name: str | None
    journey_date: date
    scheduled_departure: datetime
    actual_departure: datetime | None
    scheduled_arrival: datetime
    actual_arrival: datetime | None
    reason_for_delay: str | None
    source: str | None
    external_service_id: str | None
