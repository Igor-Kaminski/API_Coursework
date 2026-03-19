from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select

from app.models.journey_record import JourneyRecord
from app.models.route import Route
from app.models.station import Station
from app.services.import_types import JourneyImportRecord, RouteImportRecord, StationImportRecord
from app.services.journey_import_service import JourneyImportService
from app.services.route_import_service import RouteImportService
from app.services.station_import_service import StationImportService


def test_station_import_service_upserts_by_code(db_session) -> None:
    service = StationImportService()
    result = service.import_records(
        db_session,
        [
            StationImportRecord(name="Leeds", code="LDS", city="Leeds"),
            StationImportRecord(name="Leeds Station", code="LDS", city="West Yorkshire"),
        ],
    )

    station = db_session.scalar(select(Station).where(Station.code == "LDS"))

    assert result.created == 1
    assert result.updated == 1
    assert station is not None
    assert station.name == "Leeds Station"


def test_route_import_service_creates_route_from_station_codes(db_session) -> None:
    station_service = StationImportService()
    station_service.import_records(
        db_session,
        [
            StationImportRecord(name="Leeds", code="LDS", city="Leeds"),
            StationImportRecord(name="York", code="YRK", city="York"),
        ],
    )

    service = RouteImportService()
    result = service.import_records(
        db_session,
        [
            RouteImportRecord(
                origin_station_code="LDS",
                destination_station_code="YRK",
                name="Leeds to York",
                code="LDS-YRK",
                operator_name="LNER",
                distance_km=Decimal("40.20"),
            )
        ],
    )

    route = db_session.scalar(select(Route).where(Route.code == "LDS-YRK"))

    assert result.created == 1
    assert route is not None
    assert route.name == "Leeds to York"


def test_journey_import_service_derives_delay_and_status(db_session) -> None:
    station_service = StationImportService()
    station_service.import_records(
        db_session,
        [
            StationImportRecord(name="Leeds", code="LDS", city="Leeds"),
            StationImportRecord(name="York", code="YRK", city="York"),
        ],
    )

    route_service = RouteImportService()
    route_service.import_records(
        db_session,
        [
            RouteImportRecord(
                origin_station_code="LDS",
                destination_station_code="YRK",
                name="Leeds to York",
                code="LDS-YRK",
                operator_name="LNER",
            )
        ],
    )

    service = JourneyImportService()
    result = service.import_records(
        db_session,
        [
            JourneyImportRecord(
                route_code="LDS-YRK",
                origin_station_code="LDS",
                destination_station_code="YRK",
                route_name="Leeds to York",
                operator_name="LNER",
                journey_date=date(2026, 3, 4),
                scheduled_departure=datetime(2026, 3, 4, 8, 0, tzinfo=UTC),
                actual_departure=datetime(2026, 3, 4, 8, 5, tzinfo=UTC),
                scheduled_arrival=datetime(2026, 3, 4, 8, 45, tzinfo=UTC),
                actual_arrival=datetime(2026, 3, 4, 8, 50, tzinfo=UTC),
                reason_for_delay="Crew issue",
                source="test",
                external_service_id="RID-100",
            )
        ],
    )

    journey = db_session.scalar(
        select(JourneyRecord).where(JourneyRecord.external_service_id == "RID-100")
    )

    assert result.created == 1
    assert journey is not None
    assert journey.delay_minutes == 5
    assert journey.status == "delayed"
