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


def test_route_cancellation_rate_lookup_by_code(client, seeded_analytics_data) -> None:
    response = client.get("/api/v1/analytics/routes/by-code/LDS-YRK/cancellation-rate")

    assert response.status_code == 200
    assert response.json()["route_id"] == seeded_analytics_data["route_id"]
    assert response.json()["cancelled_journeys"] == 1
    assert response.json()["cancellation_rate_percentage"] == 33.33


def test_route_delay_distribution_lookup_by_code(client, seeded_analytics_data) -> None:
    response = client.get("/api/v1/analytics/routes/by-code/LDS-YRK/delay-distribution")

    assert response.status_code == 200
    assert response.json()["route_id"] == seeded_analytics_data["route_id"]
    assert response.json()["total_journeys"] == 2
    assert response.json()["buckets"][0]["bucket"] == "0-4"
