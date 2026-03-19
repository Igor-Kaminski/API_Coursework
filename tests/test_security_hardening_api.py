from sqlalchemy.exc import SQLAlchemyError
from slowapi import Limiter
from slowapi.util import get_remote_address

import app.main as app_main
from app.main import app


def test_health_endpoint_checks_database(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_endpoint_returns_503_when_database_is_unavailable(
    client,
    monkeypatch,
) -> None:
    def failing_ping_database() -> None:
        raise SQLAlchemyError("database offline")

    monkeypatch.setattr(app_main, "ping_database", failing_ping_database)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert response.json()["error"]["message"] == "database unavailable"


def test_global_database_exception_handler_returns_structured_500(
    client,
    monkeypatch,
) -> None:
    def failing_hourly_patterns(_db):
        raise SQLAlchemyError("forced failure")

    monkeypatch.setattr(
        "app.routers.analytics.analytics_service.get_hourly_delay_patterns",
        failing_hourly_patterns,
    )

    response = client.get("/api/v1/analytics/delay-patterns/hourly")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "database_error"
    assert response.json()["error"]["message"] == "database operation failed"


def test_cors_preflight_is_enabled(client) -> None:
    response = client.options(
        "/api/v1/stations",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_rate_limiting_returns_structured_429(client) -> None:
    original_limiter = app.state.limiter
    app.state.limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["2/minute"],
        headers_enabled=True,
    )
    app.state.limiter.reset()
    try:
        first = client.get("/")
        second = client.get("/")
        third = client.get("/")
    finally:
        app.state.limiter = original_limiter
        app.state.limiter.reset()

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"
    assert "rate limit exceeded" in third.json()["error"]["message"]
