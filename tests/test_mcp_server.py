import asyncio
import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.mcp import server as mcp_server
from conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def override_mcp_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("OPERATOR_API_KEY", "test-operator-key")
    monkeypatch.setenv("USER_API_KEY", "test-user-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def override_mcp_session_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "SessionFactory", TestingSessionLocal)


def _structured_tool_result(result: tuple[object, dict[str, object]]) -> object:
    _, structured_payload = result
    if "result" in structured_payload:
        return structured_payload["result"]
    return structured_payload


def test_mcp_server_registers_tools_resources_and_prompts() -> None:
    tools = asyncio.run(mcp_server.mcp.list_tools())
    resources = asyncio.run(mcp_server.mcp.list_resources())
    prompts = asyncio.run(mcp_server.mcp.list_prompts())

    tool_names = {tool.name for tool in tools}
    resource_names = {resource.name for resource in resources}
    prompt_names = {prompt.name for prompt in prompts}

    assert "search_stations" in tool_names
    assert "get_route_reliability" in tool_names
    assert "create_incident" in tool_names
    assert "Current data coverage" in resource_names
    assert "Tool guide" in resource_names
    assert "investigate_route_delay" in prompt_names


def test_search_stations_tool_returns_structured_results(
    seeded_reference_data: dict[str, int],
) -> None:
    _ = seeded_reference_data

    result = asyncio.run(mcp_server.mcp.call_tool("search_stations", {"code": "LDS"}))
    stations = _structured_tool_result(result)

    assert isinstance(stations, list)
    assert stations[0]["name"] == "Leeds"
    assert stations[0]["crs_code"] == "LDS"


def test_route_analytics_tool_supports_route_code_lookup(
    seeded_analytics_data: dict[str, int],
) -> None:
    _ = seeded_analytics_data

    result = asyncio.run(
        mcp_server.mcp.call_tool(
            "get_route_reliability",
            {"route_code": "lds-yrk"},
        )
    )
    analytics = _structured_tool_result(result)

    assert analytics["route_id"] > 0
    assert analytics["total_journeys"] == 3
    assert analytics["on_time_percentage"] == 33.33


def test_create_incident_tool_uses_same_role_model(
    db_session: Session,
    seeded_reference_data: dict[str, int],
) -> None:
    route_id = seeded_reference_data["route_id"]
    result = asyncio.run(
        mcp_server.mcp.call_tool(
            "create_incident",
            {
                "api_key": "test-user-key",
                "route_id": route_id,
                "title": "Crowding",
                "description": "Unexpected overcrowding reported",
                "incident_type": "operations",
                "severity": "medium",
                "reported_at": datetime(2026, 3, 4, 9, 0, tzinfo=UTC).isoformat(),
            },
        )
    )

    created = _structured_tool_result(result)

    assert created["success"] is True
    assert created["incident"]["title"] == "Crowding"
    assert db_session.get(mcp_server.Incident, created["incident"]["id"]) is not None


def test_data_coverage_resource_returns_json(
    seeded_analytics_data: dict[str, int],
) -> None:
    _ = seeded_analytics_data

    contents = asyncio.run(mcp_server.mcp.read_resource("rail://data-coverage"))
    payload = json.loads(contents[0].content)

    assert payload["stations"] == 2
    assert payload["routes"] == 1
    assert payload["journey_records"] == 3
