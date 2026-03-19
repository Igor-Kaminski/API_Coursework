from datetime import UTC, date, datetime

from app.models.incident import Incident
from app.models.journey_record import JourneyRecord
from app.models.route import Route


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


def test_route_cancellation_and_delay_distribution_endpoints(client, seeded_analytics_data) -> None:
    route_id = seeded_analytics_data["route_id"]

    cancellation = client.get(f"/api/v1/analytics/routes/{route_id}/cancellation-rate")
    distribution = client.get(f"/api/v1/analytics/routes/{route_id}/delay-distribution")

    assert cancellation.status_code == 200
    assert cancellation.json() == {
        "route_id": route_id,
        "total_journeys": 3,
        "cancelled_journeys": 1,
        "cancellation_rate_percentage": 33.33,
    }

    assert distribution.status_code == 200
    assert distribution.json()["route_id"] == route_id
    assert distribution.json()["total_journeys"] == 2
    assert distribution.json()["buckets"] == [
        {"bucket": "0-4", "total_journeys": 1, "percentage": 50.0},
        {"bucket": "5-9", "total_journeys": 0, "percentage": 0.0},
        {"bucket": "10-14", "total_journeys": 1, "percentage": 50.0},
        {"bucket": "15+", "total_journeys": 0, "percentage": 0.0},
    ]


def test_hourly_delay_pattern_endpoint(client, seeded_analytics_data) -> None:
    _ = seeded_analytics_data

    hourly = client.get("/api/v1/analytics/delay-patterns/hourly")

    assert hourly.status_code == 200
    assert {item["bucket"] for item in hourly.json()} == {"08:00", "09:00"}


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


def test_incident_breakdown_endpoints(client, seeded_analytics_data) -> None:
    _ = seeded_analytics_data

    severity = client.get("/api/v1/analytics/incidents/severity-breakdown")
    status = client.get("/api/v1/analytics/incidents/status-breakdown")

    assert severity.status_code == 200
    assert severity.json() == [
        {"label": "high", "total_incidents": 1},
        {"label": "medium", "total_incidents": 1},
    ]

    assert status.status_code == 200
    assert status.json() == [
        {"label": "investigating", "total_incidents": 1},
        {"label": "open", "total_incidents": 1},
    ]


def test_top_route_endpoints_rank_routes(client, db_session, seeded_analytics_data) -> None:
    leeds_id = seeded_analytics_data["leeds_id"]
    york_id = seeded_analytics_data["york_id"]

    slower_route = Route(
        origin_station_id=york_id,
        destination_station_id=leeds_id,
        name="York to Leeds",
        code="YRK-LDS",
        operator_name="Northern",
        is_active=True,
    )
    db_session.add(slower_route)
    db_session.flush()
    db_session.add_all(
        [
            JourneyRecord(
                route_id=slower_route.id,
                journey_date=date(2026, 3, 1),
                scheduled_departure=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
                actual_departure=datetime(2026, 3, 1, 11, 20, tzinfo=UTC),
                scheduled_arrival=datetime(2026, 3, 1, 11, 45, tzinfo=UTC),
                actual_arrival=datetime(2026, 3, 1, 12, 5, tzinfo=UTC),
                delay_minutes=20,
                status="delayed",
                source="test",
                external_service_id="RID-4",
            ),
            JourneyRecord(
                route_id=slower_route.id,
                journey_date=date(2026, 3, 2),
                scheduled_departure=datetime(2026, 3, 2, 12, 0, tzinfo=UTC),
                actual_departure=None,
                scheduled_arrival=datetime(2026, 3, 2, 12, 45, tzinfo=UTC),
                actual_arrival=None,
                delay_minutes=None,
                status="cancelled",
                source="test",
                external_service_id="RID-5",
            ),
        ]
    )
    db_session.add(
        Incident(
            route_id=slower_route.id,
            station_id=york_id,
            title="Crew shortage",
            description="Cancellation due to crew shortage",
            incident_type="staffing",
            severity="critical",
            status="open",
            reported_at=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
        )
    )
    db_session.commit()

    top_delayed = client.get("/api/v1/analytics/routes/top-delayed?limit=2")
    top_cancelled = client.get("/api/v1/analytics/routes/top-cancelled?limit=2")

    assert top_delayed.status_code == 200
    assert top_delayed.json()[0]["route_code"] == "YRK-LDS"
    assert top_delayed.json()[0]["average_delay_minutes"] == 20.0

    assert top_cancelled.status_code == 200
    assert top_cancelled.json()[0]["route_code"] == "YRK-LDS"
    assert top_cancelled.json()[0]["cancelled_journeys"] == 1
    assert top_cancelled.json()[0]["cancellation_rate_percentage"] == 50.0
