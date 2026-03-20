# Rail Reliability API

Coursework project for `COMP3011 Web Services and Web Data`.

This project implements a modular `FastAPI` backend for UK rail reliability and delay analytics. The design follows the coursework brief by keeping three responsibilities separate:

- reference data in `stations` and `routes`
- imported operational/history data in `journey_records`
- user-generated operational data in `incidents`

The API does not query Darwin, KB, or HSP at request time. External rail feeds are treated as ingestion sources only. Data is imported, normalized, stored in PostgreSQL, and then queried locally for public API responses and analytics.

## Features

- public read endpoints for stations, routes, incidents, and analytics
- admin-only write endpoints for station and route reference data
- role-protected incident create/update/delete flows
- modular import services for station, route, and journey datasets
- analytics for route reliability, average delay, delay patterns, station hotspots, incident frequency, and common delay reasons
- a separate MCP server with lookup, analytics, and guarded write tools
- FastAPI Swagger docs at `/docs`
- versioned Alembic migrations
- pytest coverage for incident APIs, analytics, and import services

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Pydantic v2
- Alembic
- pytest
- Uvicorn

## Repository Layout

```text
app/
  core/        config, database, security
  db/          SQLAlchemy base and model registration
  mcp/         MCP server, tools, prompts, and resources
  models/      ORM models
  routers/     API endpoint groups
  schemas/     Pydantic request/response models
  services/    analytics and import services
alembic/       database migrations
docs/          coursework-facing documentation
scripts/       ingestion and utility scripts
tests/         automated test suite
```

## Quick Access (No Installation Required)

The API is deployed and accessible at: https://rail-api-coursework.onrender.com/

- Swagger UI (interactive docs): https://rail-api-coursework.onrender.com/docs
- Health check: https://rail-api-coursework.onrender.com/health

All public read endpoints and analytics can be tested directly from the Swagger page without any local setup.

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (any recent version)

### Linux / macOS

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -e '.[dev]'
   ```

3. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

4. Start PostgreSQL and create the database:

   ```bash
   # Linux (systemd)
   sudo systemctl start postgresql
   sudo -u postgres createdb rail_api

   # macOS (Homebrew)
   brew services start postgresql
   createdb rail_api
   ```

5. Run migrations and start the API:

   ```bash
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

### Windows

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -e ".[dev]"
   ```

3. Copy `.env.example` to `.env`:

   ```powershell
   copy .env.example .env
   ```

4. Install PostgreSQL from https://www.postgresql.org/download/windows/ if not already installed. Then open a terminal and create the database:

   ```powershell
   createdb -U postgres rail_api
   ```

5. Run migrations and start the API:

   ```powershell
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

### After starting

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

The default `DATABASE_URL` in `.env.example` expects a database called `rail_api` on `localhost:5432` with user `postgres` and password `postgres`. If your local PostgreSQL uses a different user, password, or port, update `DATABASE_URL` in your `.env` accordingly.

### Optional: Load data from SQL dump

To populate the local database with the full dataset (stations, routes, journey records) without running import scripts:

```bash
psql -U postgres rail_api < rail_data.sql
```

### MCP Server

Run the MCP server for model-tool access over the same database:

```bash
python scripts/run_mcp_server.py
```

## Environment Variables

Minimum required variables are documented in `.env.example`:

- `DATABASE_URL`
- `DATABASE_ECHO`
- `ADMIN_API_KEY`
- `OPERATOR_API_KEY`
- `USER_API_KEY`
- optional rail-source settings for KB, Darwin, and HSP import workflows

Do not commit real credentials. Keep only placeholder values in tracked files.

The MCP server uses the same database and API-key values. No extra secrets are required.

## Render Deployment

This repository is now prepared for Render deployment using the included `render.yaml` blueprint.

What the blueprint provisions:

- a Python web service for the FastAPI app
- a managed PostgreSQL database
- generated API keys for admin, operator, and user roles
- automatic `alembic upgrade head` before the app starts

Basic steps on Render:

1. Push this repository to GitHub.
2. In Render, choose `New` -> `Blueprint`.
3. Connect the repository and select this project.
4. Render will create the web service and PostgreSQL database from `render.yaml`.
5. After the first deploy, open the deployed `/health` and `/docs` URLs to verify the app is live.

Important deployment note:

- the hosted PostgreSQL database will start empty
- the schema will be created automatically by Alembic
- you still need to load your station, route, journey, and incident data into the hosted database if you want the deployed API to show real analytics

Recommended post-deploy workflow:

1. deploy the blueprint
2. confirm `/health` returns `{"status":"ok","database":"ok"}`
3. run your import scripts against the hosted `DATABASE_URL`
4. verify `/api/v1/stations`, `/api/v1/routes`, `/api/v1/incidents`, and analytics endpoints

If you do not want to use the blueprint, you can still create the Render PostgreSQL database and web service manually, then use the same build and start commands:

```bash
pip install -e .
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Authentication Model

The coursework uses a deliberately simple role model based on the `X-API-Key` header:

- admin key: full station and route writes, incident management
- operator key: incident create/update/delete
- user key: incident create only
- no key required: public reads for stations, routes, incidents, and analytics

Example authenticated request:

```bash
curl -H "X-API-Key: change-me-admin-key" http://127.0.0.1:8000/api/v1/stations
```

## Main Endpoint Groups

- `GET /api/v1/stations`
- `GET /api/v1/stations/code/{station_code}`
- `GET /api/v1/stations/{station_id}`
- `POST/PATCH/DELETE /api/v1/stations/{station_id or collection}` admin only
- `GET /api/v1/routes`
- `GET /api/v1/routes/code/{route_code}`
- `GET /api/v1/routes/{route_id}`
- `POST/PATCH/DELETE /api/v1/routes/{route_id or collection}` admin only
- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{incident_id}`
- `POST /api/v1/incidents` authenticated user, operator, or admin
- `PATCH/DELETE /api/v1/incidents/{incident_id}` operator or admin
- `GET /api/v1/analytics/routes/{route_id}/reliability`
- `GET /api/v1/analytics/routes/{route_id}/average-delay`
- `GET /api/v1/analytics/routes/{route_id}/cancellation-rate`
- `GET /api/v1/analytics/routes/{route_id}/delay-distribution`
- `GET /api/v1/analytics/routes/by-code/{route_code}/reliability`
- `GET /api/v1/analytics/routes/by-code/{route_code}/average-delay`
- `GET /api/v1/analytics/routes/by-code/{route_code}/cancellation-rate`
- `GET /api/v1/analytics/routes/by-code/{route_code}/delay-distribution`
- `GET /api/v1/analytics/routes/top-delayed`
- `GET /api/v1/analytics/routes/top-cancelled`
- `GET /api/v1/analytics/delay-patterns/hourly`
- `GET /api/v1/analytics/stations/hotspots`
- `GET /api/v1/analytics/incidents/frequency`
- `GET /api/v1/analytics/incidents/severity-breakdown`
- `GET /api/v1/analytics/incidents/status-breakdown`
- `GET /api/v1/analytics/delay-reasons/common`

Useful list filters:

- stations: `code`, `name`, `city`, `crs_code`, `tiploc_code`
- routes: `code`, `name`, `origin`, `destination`, `operator_name`, `is_active`
- incidents: `route_id`, `station_id`, `incident_type`, `severity`, `status`, `reported_from`, `reported_to`

## MCP Server

The repository now includes a separate MCP server so MCP-compatible clients can query the same PostgreSQL-backed dataset without going through HTTP endpoints.

- default transport: `stdio`
- alternate transports: `sse` and `streamable-http`
- entrypoints:
  - `./.venv/bin/python scripts/run_mcp_server.py`
  - `./.venv/bin/python -m app.mcp.server`
  - `rail-api-mcp`

Useful examples:

```bash
# stdio transport for local MCP clients
./.venv/bin/python scripts/run_mcp_server.py

# streamable HTTP transport on a custom port
./.venv/bin/python scripts/run_mcp_server.py --transport streamable-http --port 8010
```

Tool coverage includes:

- station lookup and admin CRUD
- route lookup and admin CRUD
- incident lookup and CRUD with the same role rules as the HTTP API
- analytics tools for route reliability, average delay, delay patterns, hotspots, incident frequency, delay reasons, and coverage summaries
- MCP resources for overview, auth model, tool guide, and current data coverage
- MCP prompts for route-delay investigation and incident triage

Mutating MCP tools accept an `api_key` argument and enforce the same coursework role model as the FastAPI app:

- station and route writes: admin key only
- incident creation: user, operator, or admin key
- incident update/delete: operator or admin key

More detailed MCP usage notes live in `docs/mcp_server.md`.

## Import Workflow

Import order is important:

1. import station reference data
2. import or derive route reference data
3. import journey history data

Available helper scripts:

- `python scripts/import_stations.py path/to/stations.csv`
- `python scripts/import_routes.py path/to/routes.csv`
- `python scripts/import_journeys.py path/to/journeys.xml`
- `python scripts/import_darwin_snapshot.py --snapshot-path /path/to/snapshot.gz --max-services 20000`

The import services support simplified `CSV`, `JSON`, and, for journeys, `XML` inputs. Journey imports normalize status values and derive `delay_minutes` during ingestion where possible.

The Darwin importer supports two modes:

- fetch the latest FTP snapshot using local Darwin FTP environment variables
- import from an already-downloaded local snapshot file, which is useful when FTP access works better outside the app environment

Example using a local snapshot file:

```bash
DATABASE_URL="postgresql+psycopg://postgres@/rail_api?host=/run/postgresql" \
./.venv/bin/python scripts/import_darwin_snapshot.py \
  --snapshot-path "/home/igor/rail_test/downloads/20260319_161557_snapshot.gz" \
  --max-services 20000
```

Current local Darwin load achieved:

- `935` stations
- `2,911` routes
- `18,588` journey records

These imported station records currently use Darwin `TIPLOC` codes as the reference key when KB enrichment has not yet been applied.

## Current Data Coverage

After Darwin, KB, and timetable-reference enrichment, the current local database contains:

- `2,993` stations
- `2,899` routes
- `18,588` journey records

Reference data coverage:

- `2,610 / 2,993` stations have a populated `city`
- `2,912 / 2,993` stations have a populated `tiploc_code`
- `2,610 / 2,993` stations have both `latitude` and `longitude`
- `1,817 / 2,899` routes have an approximate `distance_km`

Route name coverage snapshot from `GET /api/v1/analytics/reference-data/route-name-coverage`:

- `1,959 / 2,899` routes are fully human-readable
- `820 / 2,899` are partially unresolved
- `120 / 2,899` remain fully unresolved

The remaining unresolved locations are mostly non-passenger timing points, junctions, depots, or operational aliases rather than ordinary public stations. That is why some route names still contain infrastructure-style codes.

## Testing

Run the automated tests with:

```bash
./.venv/bin/pytest
```

Current coverage focuses on:

- incident API permissions and lifecycle behavior
- analytics endpoint responses
- station, route, journey, Darwin snapshot, KB enrichment, and reference-data enrichment logic

## Live Deployment

The API is hosted on Render at: https://rail-api-coursework.onrender.com/

- Swagger UI: https://rail-api-coursework.onrender.com/docs
- Health check: https://rail-api-coursework.onrender.com/health

## Coursework Deliverables

- Technical report: [`docs/technical_report.md`](docs/technical_report.md)
- API documentation (PDF): [`docs/api_documentation.pdf`](docs/api_documentation.pdf)
- API documentation (source): [`docs/api_documentation.md`](docs/api_documentation.md)
- Presentation slides: [`docs/presentation.pptx`](docs/presentation.pptx)
- GenAI conversation logs: [`docs/conversations/`](docs/conversations/)
- SQL data dump: [`rail_data.sql`](rail_data.sql)
- Versioned source code with granular commit history
- Runnable backend with tests and migration support
