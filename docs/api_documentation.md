# Rail Reliability API Documentation

## Overview

The Rail Reliability API provides:

- public read access to station, route, incident, and analytics data
- admin-only write access for reference data
- controlled incident CRUD for authenticated users and operators
- analytics computed from locally stored relational data

Base URL during local development:

```text
http://127.0.0.1:8000
```

Versioned API prefix:

```text
/api/v1
```

## Authentication

Authentication uses the `X-API-Key` header.

Roles:

- admin: full reference-data writes and incident management
- operator: incident create/update/delete
- user: incident create only
- public: no header required for reads

Example:

```http
X-API-Key: change-me-admin-key
```

## Error Conventions

Typical error codes:

- `400` bad request for invalid payloads
- `401` missing or invalid API key
- `403` authenticated but insufficient permissions
- `404` resource not found
- `409` duplicate reference data or uniqueness conflict
- `422` request validation error

## Stations

### GET `/api/v1/stations`

Returns a paginated-style list using `limit` and `offset` query parameters.

Supported filters:

- `code`
- `name`
- `city`
- `crs_code`
- `tiploc_code`

Example response:

```json
[
  {
    "id": 1,
    "name": "Leeds",
    "code": "LDS",
    "city": "Leeds",
    "latitude": 53.794000,
    "longitude": -1.548000,
    "created_at": "2026-03-19T18:00:00Z",
    "updated_at": "2026-03-19T18:00:00Z"
  }
]
```

### GET `/api/v1/stations/{station_id}`

Returns a single station by ID.

### GET `/api/v1/stations/code/{station_code}`

Returns a single station by public station code.

### POST `/api/v1/stations`

Admin only. Creates a station.

Example request:

```json
{
  "name": "Leeds",
  "code": "LDS",
  "city": "Leeds",
  "latitude": 53.794,
  "longitude": -1.548
}
```

### PATCH `/api/v1/stations/{station_id}`

Admin only. Partially updates a station.

### DELETE `/api/v1/stations/{station_id}`

Admin only. Deletes a station.

## Routes

### GET `/api/v1/routes`

Returns routes with nested origin and destination station summaries.

Supported filters:

- `code`
- `name`
- `origin`
- `destination`
- `operator_name`
- `is_active`

### GET `/api/v1/routes/{route_id}`

Returns a single route.

### GET `/api/v1/routes/code/{route_code}`

Returns a single route by public route code.

### POST `/api/v1/routes`

Admin only. Creates a route.

Example request:

```json
{
  "origin_station_id": 1,
  "destination_station_id": 2,
  "name": "Leeds to York",
  "code": "LDS-YRK",
  "operator_name": "LNER",
  "distance_km": 40.2,
  "is_active": true
}
```

### PATCH `/api/v1/routes/{route_id}`

Admin only. Partially updates a route.

### DELETE `/api/v1/routes/{route_id}`

Admin only. Deletes a route.

## Incidents

### GET `/api/v1/incidents`

Public read access to incidents.

Supported filters:

- `route_id`
- `station_id`
- `incident_type`
- `severity`
- `status`
- `reported_from`
- `reported_to`

### GET `/api/v1/incidents/{incident_id}`

Returns one incident by ID.

### POST `/api/v1/incidents`

Requires `user`, `operator`, or `admin` key.

Example request:

```json
{
  "route_id": 1,
  "station_id": 1,
  "title": "Signal issue",
  "description": "Signal issue near Leeds",
  "incident_type": "infrastructure",
  "severity": "high",
  "status": "open",
  "reported_at": "2026-03-19T08:30:00Z"
}
```

### PATCH `/api/v1/incidents/{incident_id}`

Requires `operator` or `admin` key.

### DELETE `/api/v1/incidents/{incident_id}`

Requires `operator` or `admin` key.

## Analytics

### GET `/api/v1/analytics/routes/{route_id}/reliability`

Returns on-time, delayed, and cancelled percentages for a route.

Example response:

```json
{
  "route_id": 1,
  "total_journeys": 120,
  "on_time_percentage": 68.33,
  "delayed_percentage": 24.17,
  "cancelled_percentage": 7.5
}
```

### GET `/api/v1/analytics/routes/{route_id}/average-delay`

Returns the average delay in minutes for journeys with known delay values.

### GET `/api/v1/analytics/routes/{route_id}/cancellation-rate`

Returns the cancellation rate for a route, including total journeys and cancelled journeys.

### GET `/api/v1/analytics/routes/{route_id}/delay-distribution`

Returns a coursework-friendly delay distribution for a route using buckets:

- `0-4`
- `5-9`
- `10-14`
- `15+`

### GET `/api/v1/analytics/routes/by-code/{route_code}/reliability`

Returns route reliability using the public route code instead of the internal numeric ID.

### GET `/api/v1/analytics/routes/by-code/{route_code}/average-delay`

Returns average delay using the public route code instead of the internal numeric ID.

### GET `/api/v1/analytics/routes/by-code/{route_code}/cancellation-rate`

Returns cancellation rate using the public route code instead of the internal numeric ID.

### GET `/api/v1/analytics/routes/by-code/{route_code}/delay-distribution`

Returns the delay distribution using the public route code instead of the internal numeric ID.

### GET `/api/v1/analytics/routes/top-delayed`

Returns the most delayed routes ranked by average delay. Supports:

- `limit`
- `min_journeys`

### GET `/api/v1/analytics/routes/top-cancelled`

Returns the most cancellation-prone routes ranked by cancellation percentage. Supports:

- `limit`
- `min_journeys`

### GET `/api/v1/analytics/delay-patterns/hourly`

Returns average delay grouped by departure hour.

### GET `/api/v1/analytics/stations/hotspots`

Returns the busiest delay hotspots based on delayed journeys touching a station.

### GET `/api/v1/analytics/incidents/frequency`

Returns incident counts bucketed by report date.

### GET `/api/v1/analytics/incidents/severity-breakdown`

Returns incident counts grouped by severity.

### GET `/api/v1/analytics/incidents/status-breakdown`

Returns incident counts grouped by lifecycle status.

### GET `/api/v1/analytics/delay-reasons/common`

Returns the most common delay reasons found in imported journey data.

### GET `/api/v1/analytics/reference-data/route-name-coverage`

Returns a reference-data quality snapshot showing:

- total routes
- how many routes are fully human-readable
- how many routes still contain unresolved location codes
- the top unresolved station/location codes still affecting route names

## Import Scripts

The API does not read external feeds during public requests. Import data first, then query the API.

Commands:

```bash
python scripts/import_stations.py path/to/stations.csv
python scripts/import_routes.py path/to/routes.csv
python scripts/import_journeys.py path/to/journeys.xml
python scripts/import_darwin_snapshot.py --snapshot-path /path/to/snapshot.gz --max-services 20000
```

Supported source formats:

- stations: CSV, JSON
- routes: CSV, JSON
- journeys: CSV, JSON, XML

Darwin snapshot notes:

- the Darwin importer can fetch from FTP or import from a previously downloaded local snapshot file
- it parses Darwin `schedule` and `TS` documents and converts them into normalized station, route, and journey records
- when KB enrichment is not available yet, station reference rows are created with Darwin `TIPLOC` codes as both the code and fallback display name

Example local snapshot import:

```bash
DATABASE_URL="postgresql+psycopg://postgres@/rail_api?host=/run/postgresql" \
./.venv/bin/python scripts/import_darwin_snapshot.py \
  --snapshot-path "/home/igor/rail_test/downloads/20260319_161557_snapshot.gz" \
  --max-services 20000
```

Current local enrichment snapshot:

- `2,993` stations total
- `2,610` stations with `city`
- `2,912` stations with `tiploc_code`
- `2,610` stations with both `latitude` and `longitude`
- `2,899` routes total
- `1,817` routes with approximate `distance_km`

Current route-name coverage snapshot:

- `1,959` fully human-readable routes
- `820` partially unresolved routes
- `120` fully unresolved routes

Remaining unresolved names are mainly operational timing points, depots, sidings, or junction aliases rather than ordinary passenger stations.

## Swagger Documentation

FastAPI also exposes interactive documentation at:

- `/docs`
- `/redoc`
