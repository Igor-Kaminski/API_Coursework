def test_route_reliability_endpoint(client, seeded_analytics_data) -> None:
    route_id = seeded_analytics_data["route_id"]

    response = client.get(f"/api/v1/analytics/routes/{route_id}/reliability")

    assert response.status_code == 200
    assert response.json() == {
        "route_id": route_id,
        "total_journeys": 3,
        "on_time_percentage": 33.33,
        "delayed_percentage": 33.33,
        "cancelled_percentage": 33.33,
    }


def test_route_average_delay_endpoint(client, seeded_analytics_data) -> None:
    route_id = seeded_analytics_data["route_id"]

    response = client.get(f"/api/v1/analytics/routes/{route_id}/average-delay")

    assert response.status_code == 200
    assert response.json() == {
        "route_id": route_id,
        "total_journeys": 2,
        "average_delay_minutes": 5.0,
    }


def test_delay_pattern_endpoints(client, seeded_analytics_data) -> None:
    hourly = client.get("/api/v1/analytics/delay-patterns/hourly")
    daily = client.get("/api/v1/analytics/delay-patterns/daily")

    assert hourly.status_code == 200
    assert hourly.json()[0]["bucket"] == "08:00"
    assert daily.status_code == 200
    assert {item["bucket"] for item in daily.json()} == {"Monday", "Sunday"}


def test_station_hotspots_and_delay_reasons_endpoints(client, seeded_analytics_data) -> None:
    hotspots = client.get("/api/v1/analytics/stations/hotspots")
    reasons = client.get("/api/v1/analytics/delay-reasons/common")

    assert hotspots.status_code == 200
    assert hotspots.json()[0]["affected_journeys"] >= 1
    assert reasons.status_code == 200
    assert reasons.json()[0] == {"reason": "Signal failure", "total_occurrences": 2}


def test_incident_frequency_endpoint(client, seeded_analytics_data) -> None:
    response = client.get("/api/v1/analytics/incidents/frequency")

    assert response.status_code == 200
    assert len(response.json()) == 2
