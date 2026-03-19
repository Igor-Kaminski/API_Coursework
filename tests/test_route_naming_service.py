from app.models.incident import Incident
from app.models.journey_record import JourneyRecord
from app.models.route import Route
from app.models.station import Station
from app.services.route_naming_service import RouteNamingService
from datetime import UTC, date, datetime


def test_route_naming_service_merges_duplicate_named_routes(db_session) -> None:
    origin = Station(name="London Waterloo", code="WAT")
    destination = Station(name="Exeter St Davids", code="EXD")
    db_session.add_all([origin, destination])
    db_session.flush()

    route_one = Route(
        origin_station_id=origin.id,
        destination_station_id=destination.id,
        name="WATRLMN to EXETRSD",
        code="WATRLMN-EXETRSD",
        operator_name="SW",
        is_active=True,
    )
    route_two = Route(
        origin_station_id=origin.id,
        destination_station_id=destination.id,
        name="WAT to EXD",
        code="WAT-EXD",
        operator_name="SW",
        is_active=True,
    )
    db_session.add_all([route_one, route_two])
    db_session.flush()

    journey = JourneyRecord(
        route_id=route_two.id,
        journey_date=date(2026, 3, 19),
        scheduled_departure=datetime(2026, 3, 19, 20, 20, tzinfo=UTC),
        actual_departure=datetime(2026, 3, 19, 20, 21, tzinfo=UTC),
        scheduled_arrival=datetime(2026, 3, 19, 23, 45, tzinfo=UTC),
        actual_arrival=datetime(2026, 3, 19, 23, 47, tzinfo=UTC),
        delay_minutes=2,
        status="delayed",
        reason_for_delay=None,
        source="test",
        external_service_id="RID-ROUTE-1",
    )
    incident = Incident(
        route_id=route_two.id,
        station_id=origin.id,
        title="Test incident",
        description="Route merge test",
        incident_type="test",
        severity="low",
        status="open",
        reported_at=datetime(2026, 3, 19, 20, 0, tzinfo=UTC),
    )
    db_session.add_all([journey, incident])
    db_session.commit()

    updated = RouteNamingService().refresh_route_names(db_session)

    routes = list(db_session.query(Route).all())
    assert updated == 2
    assert len(routes) == 1
    assert routes[0].name == "London Waterloo to Exeter St Davids"
    assert journey.route_id == routes[0].id
    assert incident.route_id == routes[0].id
