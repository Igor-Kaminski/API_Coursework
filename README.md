# Transport Reliability and Delay Analytics API

This project is a final-year Web Services and Web Data coursework submission. It provides a
backend API for managing a curated transport network, recording service incidents, and exposing
analytics on disruption patterns and route reliability.

## Why This Project

The API is intentionally designed around three clear concepts:

- `Station`: admin-managed reference data
- `Route`: admin-managed transport connections
- `Incident`: dynamic operational events such as delays and cancellations

That split makes the system realistic, keeps the scope manageable, and gives the project a strong
oral-exam narrative: clean CRUD plus defendable analytics over incident history.

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Pydantic v2
- Alembic
- pytest

## Main Features

- full CRUD for incidents
- public read access for stations, routes, incidents, and analytics
- admin-protected writes for stations and routes
- operator/admin write access for incident lifecycle management
- filtering by route, station, incident type, severity, status, date range, and minimum delay
- analytics for route overview, worst travel hour, top delayed stations, and incidents by hour
- automatic Swagger/OpenAPI documentation
- migration support and seed data script
- automated tests

## Project Structure

```text
app/
  api/
  core/
  db/
  models/
  schemas/
  services/
alembic/
docs/
scripts/
tests/
```

## Setup

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -e ".[dev]"
```

3. Copy the example environment file and adjust values if needed:

```bash
cp .env.example .env
```

4. Create a PostgreSQL database that matches `DATABASE_URL`.

5. Apply migrations:

```bash
alembic upgrade head
```

6. Optionally load demo data:

```bash
python scripts/seed_reference_data.py
```

7. Run the API:

```bash
uvicorn app.main:app --reload
```

## Authentication

Protected endpoints use the `X-API-Key` header.

- admin key: full write access
- operator key: incident create/update access
- public users: GET endpoints only

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/stations" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme-admin-key" \
  -d '{"name":"Leeds","city":"Leeds","code":"LDS"}'
```

## Key Endpoints

- `GET /health`
- `GET /api/v1/stations`
- `POST /api/v1/stations`
- `GET /api/v1/routes`
- `POST /api/v1/routes`
- `GET /api/v1/incidents`
- `POST /api/v1/incidents`
- `PATCH /api/v1/incidents/{incident_id}/status`
- `GET /api/v1/analytics/routes/{route_id}/overview`
- `GET /api/v1/analytics/routes/{route_id}/worst-time`
- `GET /api/v1/analytics/stations/top-delayed`
- `GET /api/v1/analytics/incidents/by-hour`

## Documentation

- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
- Coursework API documentation PDF: `docs/api-documentation.pdf`
- Source documentation markdown: `docs/api-documentation.md`

Additional submission support files:

- Technical report outline: `docs/technical-report-outline.md`
- Presentation outline: `docs/presentation-outline.md`
- GenAI declaration template: `docs/genai-declaration.md`

## Testing

Run the test suite with:

```bash
pytest
```

The project currently includes tests for:

- station CRUD/auth behaviour
- route validation and delete conflicts
- incident CRUD, filtering, and authorization
- analytics endpoint calculations

## Example Analytics Query

```bash
curl "http://127.0.0.1:8000/api/v1/analytics/routes/1/overview?from=2026-03-10T00:00:00Z&to=2026-03-10T23:59:59Z"
```

## Coursework Notes

This repository is structured to support the oral examination as well as the code submission.
Important design decisions are intentionally easy to explain:

- FastAPI was chosen for automatic docs and validation.
- PostgreSQL was chosen for relational integrity and analytics queries.
- API keys were chosen over JWT to keep authentication meaningful but finishable.
- Reliability is modelled as an incident-based heuristic, not an official operator KPI.