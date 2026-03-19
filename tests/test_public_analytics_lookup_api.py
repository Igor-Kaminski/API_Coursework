def test_route_reliability_lookup_by_code(client, seeded_analytics_data) -> None:
    response = client.get("/api/v1/analytics/routes/by-code/LDS-YRK/reliability")

    assert response.status_code == 200
    assert response.json()["route_id"] == seeded_analytics_data["route_id"]
    assert response.json()["total_journeys"] == 3


def test_route_average_delay_lookup_by_code(client, seeded_analytics_data) -> None:
    response = client.get("/api/v1/analytics/routes/by-code/LDS-YRK/average-delay")

    assert response.status_code == 200
    assert response.json()["route_id"] == seeded_analytics_data["route_id"]
    assert response.json()["average_delay_minutes"] == 5.0
