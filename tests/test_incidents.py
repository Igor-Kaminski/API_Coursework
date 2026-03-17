from datetime import UTC, datetime

from app.models import Incident, Route, Station
from app.models.enums import IncidentStatus, IncidentType, Severity, TransportMode


def seed_route(db_session):
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
    return origin, destination, route


def test_operator_can_create_update_and_patch_incident(client, db_session, operator_headers):
    origin, _, route = seed_route(db_session)

    create_response = client.post(
        "/api/v1/incidents",
        json={
            "route_id": route.id,
            "station_id": origin.id,
            "incident_type": "delay",
            "severity": "medium",
            "status": "open",
            "title": "Overrunning engineering works",
            "description": "Late platform handover",
            "delay_minutes": 18,
            "occurred_at": "2026-03-10T08:15:00Z",
            "resolved_at": None,
        },
        headers=operator_headers,
    )
    incident_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/v1/incidents/{incident_id}",
        json={
            "route_id": route.id,
            "station_id": origin.id,
            "incident_type": "delay",
            "severity": "high",
            "status": "monitoring",
            "title": "Overrunning engineering works",
            "description": "Escalated after knock-on delays",
            "delay_minutes": 24,
            "occurred_at": "2026-03-10T08:15:00Z",
            "resolved_at": None,
        },
        headers=operator_headers,
    )

    patch_response = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "resolved", "resolved_at": "2026-03-10T09:10:00Z"},
        headers=operator_headers,
    )

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "resolved"


def test_public_can_filter_incidents(client, db_session):
    origin, destination, route = seed_route(db_session)
    db_session.add_all(
        [
            Incident(
                route_id=route.id,
                station_id=origin.id,
                incident_type=IncidentType.delay,
                severity=Severity.medium,
                status=IncidentStatus.open,
                title="Morning delay",
                delay_minutes=20,
                occurred_at=datetime(2026, 3, 10, 7, 30, tzinfo=UTC),
            ),
            Incident(
                route_id=route.id,
                station_id=destination.id,
                incident_type=IncidentType.cancellation,
                severity=Severity.high,
                status=IncidentStatus.monitoring,
                title="Service cancelled",
                delay_minutes=None,
                occurred_at=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/incidents?route_id={route.id}&status=monitoring&from=2026-03-10T00:00:00Z&to=2026-03-10T23:59:59Z"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["incident_type"] == "cancellation"


def test_create_incident_with_unrelated_station_returns_400(client, db_session, operator_headers):
    origin, destination, route = seed_route(db_session)
    extra_station = Station(name="Bradford", city="Bradford", code="BRD")
    db_session.add(extra_station)
    db_session.commit()

    response = client.post(
        "/api/v1/incidents",
        json={
            "route_id": route.id,
            "station_id": extra_station.id,
            "incident_type": "delay",
            "severity": "medium",
            "status": "open",
            "title": "Invalid station reference",
            "description": None,
            "delay_minutes": 8,
            "occurred_at": "2026-03-10T08:15:00Z",
            "resolved_at": None,
        },
        headers=operator_headers,
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "bad_request"


def test_operator_cannot_delete_incident(client, db_session, operator_headers):
    origin, _, route = seed_route(db_session)
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
    db_session.refresh(incident)

    response = client.delete(f"/api/v1/incidents/{incident.id}", headers=operator_headers)

    assert response.status_code == 403
