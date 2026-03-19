from datetime import UTC, datetime


def test_public_incident_read_returns_empty_list(client) -> None:
    response = client.get("/api/v1/incidents")

    assert response.status_code == 200
    assert response.json() == []


def test_user_can_create_incident(client, seeded_reference_data) -> None:
    payload = {
        "route_id": seeded_reference_data["route_id"],
        "station_id": seeded_reference_data["leeds_id"],
        "title": "Platform crowding",
        "description": "Crowding on platform 3",
        "incident_type": "crowding",
        "severity": "medium",
        "status": "open",
        "reported_at": datetime(2026, 3, 5, 8, 0, tzinfo=UTC).isoformat(),
    }

    response = client.post(
        "/api/v1/incidents",
        headers={"X-API-Key": "change-me-user-key"},
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["title"] == payload["title"]


def test_missing_api_key_rejects_incident_create(client, seeded_reference_data) -> None:
    payload = {
        "route_id": seeded_reference_data["route_id"],
        "station_id": seeded_reference_data["leeds_id"],
        "title": "Missing auth",
        "description": "This should fail",
        "incident_type": "access",
        "severity": "low",
        "status": "open",
        "reported_at": datetime(2026, 3, 5, 8, 0, tzinfo=UTC).isoformat(),
    }

    response = client.post("/api/v1/incidents", json=payload)

    assert response.status_code == 401


def test_user_cannot_update_incident(client, db_session, seeded_reference_data) -> None:
    create_response = client.post(
        "/api/v1/incidents",
        headers={"X-API-Key": "change-me-user-key"},
        json={
            "route_id": seeded_reference_data["route_id"],
            "station_id": seeded_reference_data["leeds_id"],
            "title": "Broken lift",
            "description": "Lift unavailable",
            "incident_type": "accessibility",
            "severity": "low",
            "status": "open",
            "reported_at": datetime(2026, 3, 5, 9, 0, tzinfo=UTC).isoformat(),
        },
    )
    incident_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers={"X-API-Key": "change-me-user-key"},
        json={"status": "resolved"},
    )

    assert response.status_code == 403


def test_operator_can_update_and_delete_incident(client, seeded_reference_data) -> None:
    create_response = client.post(
        "/api/v1/incidents",
        headers={"X-API-Key": "change-me-user-key"},
        json={
            "route_id": seeded_reference_data["route_id"],
            "station_id": seeded_reference_data["leeds_id"],
            "title": "Door fault",
            "description": "Train door fault",
            "incident_type": "rolling_stock",
            "severity": "high",
            "status": "open",
            "reported_at": datetime(2026, 3, 5, 10, 0, tzinfo=UTC).isoformat(),
        },
    )
    incident_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers={"X-API-Key": "change-me-operator-key"},
        json={"status": "resolved"},
    )
    delete_response = client.delete(
        f"/api/v1/incidents/{incident_id}",
        headers={"X-API-Key": "change-me-operator-key"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "resolved"
    assert delete_response.status_code == 204
