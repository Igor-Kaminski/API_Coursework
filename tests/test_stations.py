from datetime import UTC, datetime

from app.models import Incident, Route, Station
from app.models.enums import IncidentStatus, IncidentType, Severity, TransportMode


def test_public_station_listing_returns_seeded_stations(client, db_session):
    db_session.add_all(
        [
            Station(name="Leeds", city="Leeds", code="LDS"),
            Station(name="York", city="York", code="YRK"),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/stations")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["city"] in {"Leeds", "York"}


def test_admin_can_create_station(client, admin_headers):
    response = client.post(
        "/api/v1/stations",
        json={"name": "Manchester Piccadilly", "city": "Manchester", "code": "MAN"},
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["code"] == "MAN"


def test_operator_cannot_create_station(client, operator_headers):
    response = client.post(
        "/api/v1/stations",
        json={"name": "Huddersfield", "city": "Huddersfield", "code": "HUD"},
        headers=operator_headers,
    )

    assert response.status_code == 403


def test_delete_station_returns_conflict_when_station_is_referenced(client, db_session, admin_headers):
    station_a = Station(name="Leeds", city="Leeds", code="LDS")
    station_b = Station(name="York", city="York", code="YRK")
    db_session.add_all([station_a, station_b])
    db_session.commit()
    db_session.refresh(station_a)
    db_session.refresh(station_b)

    route = Route(
        name="Northern Express",
        origin_station_id=station_a.id,
        destination_station_id=station_b.id,
        transport_mode=TransportMode.train,
        active=True,
    )
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)

    incident = Incident(
        route_id=route.id,
        station_id=station_a.id,
        incident_type=IncidentType.delay,
        severity=Severity.medium,
        status=IncidentStatus.open,
        title="Signal check",
        delay_minutes=12,
        occurred_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
    )
    db_session.add(incident)
    db_session.commit()

    response = client.delete(f"/api/v1/stations/{station_a.id}", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["error_code"] == "conflict"
