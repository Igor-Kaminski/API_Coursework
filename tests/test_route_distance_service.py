from decimal import Decimal

from app.models.route import Route
from app.models.station import Station
from app.services.route_distance_service import RouteDistanceService


def test_route_distance_service_backfills_distance(db_session) -> None:
    leeds = Station(
        name="Leeds",
        code="LDS",
        crs_code="LDS",
        latitude=Decimal("53.794897"),
        longitude=Decimal("-1.547435"),
    )
    york = Station(
        name="York",
        code="YRK",
        crs_code="YRK",
        latitude=Decimal("53.957979"),
        longitude=Decimal("-1.093177"),
    )
    db_session.add_all([leeds, york])
    db_session.flush()

    route = Route(
        origin_station_id=leeds.id,
        destination_station_id=york.id,
        name="Leeds to York",
        code="LDS-YRK",
        operator_name="LNER",
        is_active=True,
    )
    db_session.add(route)
    db_session.commit()

    updated = RouteDistanceService().backfill_distances(db_session)
    db_session.refresh(route)

    assert updated == 1
    assert route.distance_km is not None
    assert route.distance_km > 0
