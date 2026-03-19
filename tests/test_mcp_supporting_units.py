from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core import database as database_module
from app.mcp import auth as mcp_auth
from app.mcp import server as mcp_server
from app.models.incident import Incident
from app.models.route import Route
from app.models.station import Station
from conftest import TestingSessionLocal, engine as test_engine


@pytest.fixture(autouse=True)
def override_mcp_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("OPERATOR_API_KEY", "test-operator-key")
    monkeypatch.setenv("USER_API_KEY", "test-user-key")
    get_settings.cache_clear()
    monkeypatch.setattr(mcp_server, "SessionFactory", TestingSessionLocal)
    yield
    get_settings.cache_clear()


def test_mcp_auth_helpers_validate_roles() -> None:
    assert mcp_auth.resolve_api_role("test-admin-key") == mcp_server.Role.ADMIN
    assert mcp_auth.resolve_api_role("test-operator-key") == mcp_server.Role.OPERATOR
    assert mcp_auth.resolve_api_role("test-user-key") == mcp_server.Role.USER
    assert (
        mcp_auth.require_api_role("test-admin-key", mcp_server.Role.ADMIN)
        == mcp_server.Role.ADMIN
    )

    with pytest.raises(ValueError, match="api_key is required"):
        mcp_auth.resolve_api_role(None)

    with pytest.raises(ValueError, match="invalid API key"):
        mcp_auth.resolve_api_role("bad-key")

    with pytest.raises(ValueError, match="insufficient permissions"):
        mcp_auth.require_api_role("test-user-key", mcp_server.Role.ADMIN)


def test_database_helpers_ping_dispose_and_session_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    fake_session = FakeSession()
    monkeypatch.setattr(database_module, "SessionLocal", lambda: fake_session)

    generator = database_module.get_db_session()
    assert next(generator) is fake_session
    with pytest.raises(StopIteration):
        next(generator)
    assert fake_session.closed is True

    monkeypatch.setattr(database_module, "engine", test_engine)
    database_module.ping_database()

    class DisposableEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    disposable = DisposableEngine()
    monkeypatch.setattr(database_module, "engine", disposable)
    database_module.dispose_engine()
    assert disposable.disposed is True

    class BrokenEngine:
        def dispose(self) -> None:
            raise SQLAlchemyError("boom")

    monkeypatch.setattr(database_module, "engine", BrokenEngine())
    database_module.dispose_engine()


def test_mcp_helper_functions_cover_lookup_and_serialization(
    db_session,
    seeded_analytics_data: dict[str, int],
) -> None:
    route_id = seeded_analytics_data["route_id"]
    leeds_id = seeded_analytics_data["leeds_id"]
    york_id = seeded_analytics_data["york_id"]

    assert mcp_server._to_json_compatible(Decimal("1.25")) == 1.25
    assert mcp_server._to_json_compatible(datetime(2026, 3, 1, tzinfo=UTC)).startswith(
        "2026-03-01"
    )
    assert mcp_server._to_json_compatible({"items": [Decimal("2.50")]}) == {
        "items": [2.5]
    }

    leeds = db_session.get(Station, leeds_id)
    york = db_session.get(Station, york_id)
    route = db_session.get(Route, route_id)
    assert leeds is not None and york is not None and route is not None

    assert mcp_server._fetch_station(db_session, station_id=leeds_id).name == "Leeds"
    assert mcp_server._fetch_station(db_session, code="LDS").id == leeds_id
    assert mcp_server._fetch_station(db_session, crs_code="YRK").id == york_id
    assert mcp_server._fetch_station(db_session, tiploc_code="LEEDS").id == leeds_id

    with pytest.raises(ValueError, match="provide station_id, code, crs_code, or tiploc_code"):
        mcp_server._fetch_station(db_session)

    with pytest.raises(ValueError, match="station not found"):
        mcp_server._fetch_station(db_session, code="BAD")

    assert mcp_server._fetch_route(db_session, route_id=route_id).name == "Leeds to York"
    assert mcp_server._fetch_route(db_session, code="LDS-YRK").id == route_id

    with pytest.raises(ValueError, match="provide route_id or code"):
        mcp_server._fetch_route(db_session)

    with pytest.raises(ValueError, match="route not found"):
        mcp_server._fetch_route(db_session, code="BAD")

    mcp_server._validate_station_ids(db_session, leeds_id, york_id)
    with pytest.raises(ValueError, match="origin station not found"):
        mcp_server._validate_station_ids(db_session, 999, york_id)
    with pytest.raises(ValueError, match="destination station not found"):
        mcp_server._validate_station_ids(db_session, leeds_id, 999)

    mcp_server._validate_incident_scope(db_session, route_id, leeds_id)
    with pytest.raises(ValueError, match="either route_id or station_id must be provided"):
        mcp_server._validate_incident_scope(db_session, None, None)

    dumped = mcp_server._dump_model(
        mcp_server.analytics_service.get_route_reliability(db_session, route_id)
    )
    assert dumped["total_journeys"] == 3
    assert mcp_server._serialize_station(leeds)["crs_code"] == "LDS"
    assert mcp_server._serialize_route(route)["origin_station"]["name"] == "Leeds"

    incident = db_session.query(Incident).first()
    assert incident is not None
    assert mcp_server._serialize_incident(incident)["title"] == incident.title


def test_mcp_search_lookup_and_analytics_impls(
    seeded_analytics_data: dict[str, int],
) -> None:
    route_id = seeded_analytics_data["route_id"]
    leeds_id = seeded_analytics_data["leeds_id"]

    assert mcp_server.search_stations_impl(name="lee")[0]["code"] == "LDS"
    assert mcp_server.get_station_impl(code="LDS")["name"] == "Leeds"
    assert mcp_server.search_routes_impl(origin="LDS", destination="YRK")[0]["code"] == "LDS-YRK"
    assert mcp_server.get_route_impl(code="LDS-YRK")["id"] == route_id
    assert mcp_server.list_incidents_impl(route_id=route_id)[0]["route_id"] == route_id
    assert mcp_server.get_incident_impl(1)["route_id"] == route_id

    assert mcp_server.get_route_reliability_impl(route_code="LDS-YRK")["total_journeys"] == 3
    assert mcp_server.get_route_average_delay_impl(route_id=route_id)["average_delay_minutes"] == 5.0
    assert mcp_server.get_route_cancellation_rate_impl(route_id=route_id)["cancelled_journeys"] == 1
    assert mcp_server.get_route_delay_distribution_impl(route_id=route_id)["total_journeys"] == 2
    assert mcp_server.get_hourly_delay_patterns_impl()[0]["bucket"] == "08:00"
    assert mcp_server.get_station_hotspots_impl(limit=2)[0]["station_id"] in {leeds_id, 2}
    assert mcp_server.get_incident_frequency_impl()[0]["total_incidents"] >= 1
    assert mcp_server.get_incident_severity_breakdown_impl()[0]["label"] == "high"
    assert mcp_server.get_incident_status_breakdown_impl()[0]["label"] == "investigating"
    assert mcp_server.get_common_delay_reasons_impl(limit=1)[0]["reason"] == "Signal failure"
    assert mcp_server.get_top_delayed_routes_impl(limit=1)[0]["route_code"] == "LDS-YRK"
    assert mcp_server.get_top_cancelled_routes_impl(limit=1)[0]["route_code"] == "LDS-YRK"
    assert mcp_server.get_route_name_coverage_impl()["total_routes"] == 1
    assert mcp_server.get_data_coverage_impl()["journey_records"] == 3


def test_mcp_write_impls_wrappers_resources_prompts_and_main(
    seeded_analytics_data: dict[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leeds_id = seeded_analytics_data["leeds_id"]
    york_id = seeded_analytics_data["york_id"]

    created_station = mcp_server.create_station_impl(
        api_key="test-admin-key",
        name="Harrogate",
        code="HRG",
        crs_code="HRG",
        city="Harrogate",
    )
    station_id = created_station["station"]["id"]
    assert created_station["success"] is True

    updated_station = mcp_server.update_station(
        api_key="test-admin-key",
        station_id=station_id,
        city="North Yorkshire",
    )
    assert updated_station["station"]["city"] == "North Yorkshire"
    assert mcp_server.get_station(code="HRG")["id"] == station_id

    created_route = mcp_server.create_route(
        api_key="test-admin-key",
        origin_station_id=leeds_id,
        destination_station_id=station_id,
        name="Leeds to Harrogate",
        code="LDS-HRG",
        operator_name="Northern",
    )
    route_id = created_route["route"]["id"]
    assert created_route["route"]["code"] == "LDS-HRG"
    assert mcp_server.search_routes(code="LDS-HRG")[0]["id"] == route_id
    assert mcp_server.get_route(code="LDS-HRG")["id"] == route_id

    updated_route = mcp_server.update_route(
        api_key="test-admin-key",
        route_id=route_id,
        destination_station_id=york_id,
        name="Leeds to York Duplicate Test",
        code="LDS-YRK-2",
        is_active=False,
    )
    assert updated_route["route"]["code"] == "LDS-YRK-2"
    assert updated_route["route"]["is_active"] is False

    created_incident = mcp_server.create_incident(
        api_key="test-user-key",
        route_id=route_id,
        title="Minor delay",
        description="Temporary crowding",
        incident_type="crowding",
        severity="low",
        reported_at=datetime(2026, 3, 6, 8, 0, tzinfo=UTC),
    )
    incident_id = created_incident["incident"]["id"]
    assert mcp_server.list_incidents(route_id=route_id)[0]["id"] == incident_id
    assert mcp_server.get_incident(incident_id)["id"] == incident_id

    updated_incident = mcp_server.update_incident(
        api_key="test-operator-key",
        incident_id=incident_id,
        status="resolved",
    )
    assert updated_incident["incident"]["status"] == "resolved"

    assert mcp_server.delete_incident(api_key="test-admin-key", incident_id=incident_id) == {
        "success": True,
        "deleted_incident_id": incident_id,
    }
    assert mcp_server.delete_route(api_key="test-admin-key", route_id=route_id) == {
        "success": True,
        "deleted_route_id": route_id,
    }
    assert mcp_server.delete_station(api_key="test-admin-key", station_id=station_id) == {
        "success": True,
        "deleted_station_id": station_id,
    }

    with pytest.raises(ValueError, match="invalid API key"):
        mcp_server.create_station_impl(api_key="bad-key", name="Bad")
    with pytest.raises(ValueError, match="station not found"):
        mcp_server.update_station_impl(api_key="test-admin-key", station_id=999, name="Missing")
    with pytest.raises(ValueError, match="duplicate route definition"):
        mcp_server.create_route_impl(
            api_key="test-admin-key",
            origin_station_id=leeds_id,
            destination_station_id=york_id,
            name="Leeds to York",
            code="OTHER",
        )
    with pytest.raises(ValueError, match="incident not found"):
        mcp_server.delete_incident_impl(api_key="test-admin-key", incident_id=999)

    assert "advanced_feature" in mcp_server.overview_resource()
    assert "api_key_parameter" in mcp_server.auth_model_resource()
    assert "lookup_tools" in mcp_server.tool_guide_resource()
    assert "stations" in mcp_server.data_coverage_resource()
    assert "get_route_reliability" in mcp_server.investigate_route_delay_prompt("LDS-YRK")
    assert "list_incidents" in mcp_server.triage_recent_incidents_prompt()

    parser = mcp_server.build_arg_parser()
    parsed = parser.parse_args(["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8123"])
    assert parsed.transport == "streamable-http"
    assert parsed.host == "0.0.0.0"
    assert parsed.port == 8123

    called: dict[str, object] = {}

    def fake_run(transport: str) -> None:
        called["transport"] = transport

    monkeypatch.setattr(mcp_server.mcp, "run", fake_run)
    mcp_server.main(["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8123"])
    assert called["transport"] == "streamable-http"
    assert mcp_server.mcp.settings.host == "0.0.0.0"
    assert mcp_server.mcp.settings.port == 8123
