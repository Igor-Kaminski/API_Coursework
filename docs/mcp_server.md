# MCP Server

This repository includes a separate Model Context Protocol server that exposes the coursework dataset as MCP tools, resources, and prompts.

## Purpose

The MCP server is an advanced feature layered over the same PostgreSQL database used by the FastAPI app. It does not replace the HTTP API. Instead, it gives MCP-compatible clients direct access to:

- station lookup and reference-data administration
- route lookup and reference-data administration
- incident lookup and lifecycle management
- analytics over stored `journey_records`
- project metadata and coverage summaries

This keeps the design defendable for coursework:

- FastAPI remains the primary web-service interface
- PostgreSQL remains the single source of truth
- MCP is a separate integration surface, not a second business-logic implementation

## Entrypoints

You can run the server in any of these ways:

```bash
./.venv/bin/python scripts/run_mcp_server.py
./.venv/bin/python -m app.mcp.server
rail-api-mcp
```

Default transport is `stdio`, which is the normal choice for local MCP clients.

## Transport Options

### `stdio`

```bash
./.venv/bin/python scripts/run_mcp_server.py
```

### `sse`

```bash
./.venv/bin/python scripts/run_mcp_server.py --transport sse --host 127.0.0.1 --port 8010
```

### `streamable-http`

```bash
./.venv/bin/python scripts/run_mcp_server.py --transport streamable-http --host 127.0.0.1 --port 8010
```

## Authentication Rules

Read tools are public, matching the HTTP API design.

Mutating tools require an `api_key` argument:

- station and route create/update/delete: admin key
- incident create: user, operator, or admin key
- incident update/delete: operator or admin key

The keys are read from the same environment variables already used by the FastAPI app:

- `ADMIN_API_KEY`
- `OPERATOR_API_KEY`
- `USER_API_KEY`

## Tool Groups

Lookup and CRUD tools:

- `search_stations`
- `get_station`
- `create_station`
- `update_station`
- `delete_station`
- `search_routes`
- `get_route`
- `create_route`
- `update_route`
- `delete_route`
- `list_incidents`
- `get_incident`
- `create_incident`
- `update_incident`
- `delete_incident`

Analytics tools:

- `get_route_reliability`
- `get_route_average_delay`
- `get_hourly_delay_patterns`
- `get_daily_delay_patterns`
- `get_station_hotspots`
- `get_incident_frequency`
- `get_common_delay_reasons`
- `get_route_name_coverage`
- `get_data_coverage`

## Resources

The server exposes static and dynamic MCP resources:

- `rail://overview`
- `rail://auth-model`
- `rail://data-coverage`
- `rail://tool-guide`

These are useful for clients that want metadata before calling tools.

## Prompts

The server also exposes reusable MCP prompts:

- `investigate_route_delay`
- `triage_recent_incidents`

They provide structured guidance for clients that want help sequencing tool calls.

## Notes

- The MCP server uses direct SQLAlchemy database access for low-friction local integration.
- It reuses the same domain models and analytics service as the FastAPI app.
- It is intended for local or controlled coursework use, not as a public internet-facing service.
