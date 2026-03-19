from datetime import UTC, datetime


def test_incident_list_filters_by_route_station_and_status(client, seeded_analytics_data) -> None:
    route_id = seeded_analytics_data["route_id"]
    station_id = seeded_analytics_data["leeds_id"]

    by_route = client.get(f"/api/v1/incidents?route_id={route_id}")
    by_station = client.get(f"/api/v1/incidents?station_id={station_id}")
    by_status = client.get("/api/v1/incidents?status=open")

    assert by_route.status_code == 200
    assert len(by_route.json()) == 2
    assert by_station.status_code == 200
    assert len(by_station.json()) == 1
    assert by_station.json()[0]["station_id"] == station_id
    assert by_status.status_code == 200
    assert all(item["status"] == "open" for item in by_status.json())


def test_incident_list_filters_by_type_severity_and_date_range(client, seeded_analytics_data) -> None:
    by_type = client.get("/api/v1/incidents?incident_type=weather")
    by_severity = client.get("/api/v1/incidents?severity=high")
    by_date = client.get(
        "/api/v1/incidents",
        params={
            "reported_from": datetime(2026, 3, 2, 0, 0, tzinfo=UTC).isoformat(),
            "reported_to": datetime(2026, 3, 2, 23, 59, tzinfo=UTC).isoformat(),
        },
    )

    assert by_type.status_code == 200
    assert len(by_type.json()) == 1
    assert by_type.json()[0]["incident_type"] == "weather"

    assert by_severity.status_code == 200
    assert len(by_severity.json()) == 1
    assert by_severity.json()[0]["severity"] == "high"

    assert by_date.status_code == 200
    assert len(by_date.json()) == 1
    assert by_date.json()[0]["reported_at"].startswith("2026-03-02")
