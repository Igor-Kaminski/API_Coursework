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
  models/      ORM models
  routers/     API endpoint groups
  schemas/     Pydantic request/response models
  services/    analytics and import services
alembic/       database migrations
docs/          coursework-facing documentation
scripts/       ingestion and utility scripts
tests/         automated test suite
```

## Setup

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Install dependencies:

   ```bash
   ./.venv/bin/pip install -e ".[dev]"
   ```

3. Copy `.env.example` to `.env` and fill in local values:

   ```bash
   cp .env.example .env
   ```

4. Create the PostgreSQL database referenced by `DATABASE_URL`.

5. Run migrations:

   ```bash
   ./.venv/bin/alembic upgrade head
   ```

6. Start the API:

   ```bash
   ./.venv/bin/uvicorn app.main:app --reload
   ```

7. Open the interactive docs:

   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

## Environment Variables

Minimum required variables are documented in `.env.example`:

- `DATABASE_URL`
- `DATABASE_ECHO`
- `ADMIN_API_KEY`
- `OPERATOR_API_KEY`
- `USER_API_KEY`
- optional rail-source settings for KB, Darwin, and HSP import workflows

Do not commit real credentials. Keep only placeholder values in tracked files.

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
- `GET /api/v1/analytics/routes/by-code/{route_code}/reliability`
- `GET /api/v1/analytics/routes/by-code/{route_code}/average-delay`
- `GET /api/v1/analytics/delay-patterns/hourly`
- `GET /api/v1/analytics/delay-patterns/daily`
- `GET /api/v1/analytics/stations/hotspots`
- `GET /api/v1/analytics/incidents/frequency`
- `GET /api/v1/analytics/delay-reasons/common`

Useful list filters:

- stations: `code`, `name`, `city`, `crs_code`, `tiploc_code`
- routes: `code`, `name`, `origin`, `destination`, `operator_name`, `is_active`
- incidents: `route_id`, `station_id`, `incident_type`, `severity`, `status`, `reported_from`, `reported_to`

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

## Coursework Deliverables

- API documentation PDF: [`docs/api_documentation.pdf`](docs/api_documentation.pdf)
- API documentation source: [`docs/api_documentation.md`](docs/api_documentation.md)
- versioned source code with granular commit history
- runnable backend with tests and migration support

The technical report, GenAI declaration, conversation logs, and presentation slides can be added alongside this repository for final submission.
