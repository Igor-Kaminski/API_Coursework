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

### GET `/api/v1/routes/{route_id}`

Returns a single route.

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

### GET `/api/v1/analytics/delay-patterns/hourly`

Returns average delay grouped by departure hour.

### GET `/api/v1/analytics/delay-patterns/daily`

Returns average delay grouped by weekday.

### GET `/api/v1/analytics/stations/hotspots`

Returns the busiest delay hotspots based on delayed journeys touching a station.

### GET `/api/v1/analytics/incidents/frequency`

Returns incident counts bucketed by report date.

### GET `/api/v1/analytics/delay-reasons/common`

Returns the most common delay reasons found in imported journey data.

## Import Scripts

The API does not read external feeds during public requests. Import data first, then query the API.

Commands:

```bash
python scripts/import_stations.py path/to/stations.csv
python scripts/import_routes.py path/to/routes.csv
python scripts/import_journeys.py path/to/journeys.xml
```

Supported source formats:

- stations: CSV, JSON
- routes: CSV, JSON
- journeys: CSV, JSON, XML

## Swagger Documentation

FastAPI also exposes interactive documentation at:

- `/docs`
- `/redoc`
