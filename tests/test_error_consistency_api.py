from datetime import UTC, datetime


def test_not_found_errors_use_consistent_shape(client, seeded_reference_data) -> None:
    _ = seeded_reference_data

    responses = [
        client.get("/api/v1/stations/9999"),
        client.get("/api/v1/routes/code/UNKNOWN"),
        client.get("/api/v1/incidents/9999"),
        client.get("/api/v1/analytics/routes/by-code/UNKNOWN/reliability"),
    ]

    for response in responses:
        body = response.json()
        assert response.status_code == 404
        assert body["error"]["code"] == "not_found"
        assert body["error"]["path"].startswith("/api/v1/")
        assert body["error"]["message"].endswith("not found")


def test_duplicate_creates_return_409_conflict(client, seeded_reference_data) -> None:
    payload = {
        "name": "Leeds Duplicate",
        "code": "LDS",
        "city": "Leeds",
    }

    response = client.post(
        "/api/v1/stations",
        headers={"X-API-Key": "change-me-admin-key"},
        json=payload,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert "already exists" in response.json()["error"]["message"]


def test_validation_errors_are_wrapped_cleanly(client, seeded_reference_data) -> None:
    response = client.post(
        "/api/v1/incidents",
        headers={"X-API-Key": "change-me-user-key"},
        json={
            "route_id": seeded_reference_data["route_id"],
            "station_id": seeded_reference_data["leeds_id"],
            "description": "Missing title should fail",
            "incident_type": "access",
            "severity": "low",
            "status": "open",
            "reported_at": datetime(2026, 3, 5, 8, 0, tzinfo=UTC).isoformat(),
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "request validation failed"
    assert any(detail["field"] == "title" for detail in body["error"]["details"])


def test_delete_conflicts_are_explained(client, seeded_analytics_data) -> None:
    station_response = client.delete(
        f"/api/v1/stations/{seeded_analytics_data['leeds_id']}",
        headers={"X-API-Key": "change-me-admin-key"},
    )
    route_response = client.delete(
        f"/api/v1/routes/{seeded_analytics_data['route_id']}",
        headers={"X-API-Key": "change-me-admin-key"},
    )

    assert station_response.status_code == 409
    assert station_response.json()["error"]["code"] == "conflict"
    assert "referenced by routes or incidents" in station_response.json()["error"]["message"]

    assert route_response.status_code == 409
    assert route_response.json()["error"]["code"] == "conflict"
    assert "referenced by journey records or incidents" in route_response.json()["error"]["message"]


def test_code_lookups_and_filters_are_case_insensitive_and_trimmed(
    client,
    seeded_analytics_data,
) -> None:
    station = client.get("/api/v1/stations/code/lds")
    route = client.get("/api/v1/routes/code/lds-yrk")
    analytics = client.get("/api/v1/analytics/routes/by-code/lds-yrk/reliability")
    station_filter = client.get("/api/v1/stations?name=%20lee%20")
    route_filter = client.get("/api/v1/routes?origin=%20lds%20&destination=%20yrk%20")

    assert station.status_code == 200
    assert station.json()["code"] == "LDS"

    assert route.status_code == 200
    assert route.json()["code"] == "LDS-YRK"

    assert analytics.status_code == 200
    assert analytics.json()["route_id"] == seeded_analytics_data["route_id"]

    assert station_filter.status_code == 200
    assert len(station_filter.json()) == 1
    assert station_filter.json()[0]["name"] == "Leeds"

    assert route_filter.status_code == 200
    assert len(route_filter.json()) == 1
    assert route_filter.json()[0]["code"] == "LDS-YRK"


def test_invalid_filter_range_returns_clean_validation_error(client) -> None:
    response = client.get(
        "/api/v1/incidents?reported_from=2026-03-05T12:00:00Z&reported_to=2026-03-05T08:00:00Z"
    )

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert "reported_from" in body["error"]["message"]
