from datetime import UTC, datetime

from app.models import Incident, Route, Station
from app.models.enums import IncidentStatus, IncidentType, Severity, TransportMode


def test_admin_can_create_route(client, db_session, admin_headers):
    origin = Station(name="Leeds", city="Leeds", code="LDS")
    destination = Station(name="York", city="York", code="YRK")
    db_session.add_all([origin, destination])
    db_session.commit()

    response = client.post(
        "/api/v1/routes",
        json={
            "name": "TransPennine 101",
            "origin_station_id": origin.id,
            "destination_station_id": destination.id,
            "transport_mode": "train",
            "active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["transport_mode"] == "train"


def test_route_validation_rejects_same_origin_and_destination(client, admin_headers):
    response = client.post(
        "/api/v1/routes",
        json={
            "name": "Circular Route",
            "origin_station_id": 1,
            "destination_station_id": 1,
            "transport_mode": "bus",
            "active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_delete_route_returns_conflict_when_incidents_exist(client, db_session, admin_headers):
    origin = Station(name="Leeds", city="Leeds", code="LDS")
    destination = Station(name="York", city="York", code="YRK")
    db_session.add_all([origin, destination])
    db_session.commit()
    db_session.refresh(origin)
    db_session.refresh(destination)

    route = Route(
        name="Northern Express",
        origin_station_id=origin.id,
        destination_station_id=destination.id,
        transport_mode=TransportMode.train,
    )
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)

    incident = Incident(
        route_id=route.id,
        station_id=origin.id,
        incident_type=IncidentType.delay,
        severity=Severity.low,
        status=IncidentStatus.open,
        title="Minor delay",
        delay_minutes=5,
        occurred_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
    )
    db_session.add(incident)
    db_session.commit()

    response = client.delete(f"/api/v1/routes/{route.id}", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Route cannot be deleted while incidents reference it."
