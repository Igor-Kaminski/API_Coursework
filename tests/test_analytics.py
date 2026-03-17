from datetime import UTC, datetime

from app.models import Incident, Route, Station
from app.models.enums import IncidentStatus, IncidentType, Severity, TransportMode


def seed_analytics_data(db_session) -> tuple[Station, Station, Route]:
    leeds = Station(name="Leeds", city="Leeds", code="LDS")
    york = Station(name="York", city="York", code="YRK")
    db_session.add_all([leeds, york])
    db_session.commit()
    db_session.refresh(leeds)
    db_session.refresh(york)

    route = Route(
        name="Northern Express",
        origin_station_id=leeds.id,
        destination_station_id=york.id,
        transport_mode=TransportMode.train,
    )
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)

    db_session.add_all(
        [
            Incident(
                route_id=route.id,
                station_id=leeds.id,
                incident_type=IncidentType.delay,
                severity=Severity.medium,
                status=IncidentStatus.open,
                title="Morning platform congestion",
                delay_minutes=18,
                occurred_at=datetime(2026, 3, 10, 7, 0, tzinfo=UTC),
            ),
            Incident(
                route_id=route.id,
                station_id=leeds.id,
                incident_type=IncidentType.cancellation,
                severity=Severity.critical,
                status=IncidentStatus.resolved,
                title="Fleet fault",
                delay_minutes=None,
                occurred_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
                resolved_at=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
            ),
            Incident(
                route_id=route.id,
                station_id=york.id,
                incident_type=IncidentType.delay,
                severity=Severity.high,
                status=IncidentStatus.monitoring,
                title="Crew displacement",
                delay_minutes=35,
                occurred_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
            ),
        ]
    )
    db_session.commit()
    return leeds, york, route


def test_route_overview_returns_expected_metrics(client, db_session):
    _, _, route = seed_analytics_data(db_session)

    response = client.get(
        f"/api/v1/analytics/routes/{route.id}/overview?from=2026-03-10T00:00:00Z&to=2026-03-10T23:59:59Z"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_count"] == 3
    assert payload["cancellation_count"] == 1
    assert payload["severe_incident_count"] == 2
    assert payload["reliability_score"] < 100


def test_route_worst_time_selects_highest_disruption_hour(client, db_session):
    _, _, route = seed_analytics_data(db_session)

    response = client.get(
        f"/api/v1/analytics/routes/{route.id}/worst-time?from=2026-03-10T00:00:00Z&to=2026-03-10T23:59:59Z"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["worst_hour"] == 8
    assert payload["incident_count"] == 2


def test_top_delayed_stations_orders_by_total_delay(client, db_session):
    _, _, route = seed_analytics_data(db_session)

    response = client.get(
        "/api/v1/analytics/stations/top-delayed?limit=2&from=2026-03-10T00:00:00Z&to=2026-03-10T23:59:59Z"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["station_name"] == "York"
    assert payload[0]["total_delay_minutes"] == 35


def test_incidents_by_hour_returns_grouped_counts(client, db_session):
    seed_analytics_data(db_session)

    response = client.get("/api/v1/analytics/incidents/by-hour?from=2026-03-10T00:00:00Z&to=2026-03-10T23:59:59Z")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["hour"] == 7
    assert payload[1]["hour"] == 8
    assert payload[1]["incident_count"] == 2
