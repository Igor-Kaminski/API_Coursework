# Transport Reliability and Delay Analytics API

## Overview

This API manages a curated transport network and records operational incidents such as delays,
cancellations, weather disruption, staff shortages, and signalling issues. It is designed for
coursework assessment with a focus on realistic domain modelling, analytics, testing, and
explainable engineering decisions.

Base URL when running locally:

- http://127.0.0.1:8000

API prefix:

- /api/v1

## Authentication

Protected write endpoints use the `X-API-Key` header.

- Admin key: full write access to stations, routes, and incidents
- Operator key: create and update incidents only
- Public users: read-only access to GET endpoints

Example header:

X-API-Key: changeme-admin-key

## Status Codes

- 200 OK: successful read or update
- 201 Created: resource created
- 204 No Content: resource deleted
- 400 Bad Request: invalid query logic or invalid route/station combination
- 401 Unauthorized: missing or invalid API key
- 403 Forbidden: authenticated but insufficient role
- 404 Not Found: resource does not exist
- 409 Conflict: duplicate data or delete blocked by references
- 422 Unprocessable Entity: validation failure

## Utility Endpoint

GET /health

- Returns a simple readiness payload

Example response:

{
  "status": "ok"
}

## Stations

GET /api/v1/stations

- Optional filters: city, limit, offset

GET /api/v1/stations/{station_id}

POST /api/v1/stations

- Admin only
- Body fields: name, city, code

PUT /api/v1/stations/{station_id}

- Admin only

DELETE /api/v1/stations/{station_id}

- Admin only
- Returns 409 if the station is referenced by routes or incidents

Example create request:

{
  "name": "Manchester Piccadilly",
  "city": "Manchester",
  "code": "MAN"
}

## Routes

GET /api/v1/routes

- Optional filters: transport_mode, origin_station_id, destination_station_id, active, limit, offset

GET /api/v1/routes/{route_id}

POST /api/v1/routes

- Admin only
- Requires valid origin and destination station IDs

PUT /api/v1/routes/{route_id}

- Admin only

DELETE /api/v1/routes/{route_id}

- Admin only
- Returns 409 if incidents still reference the route

Example create request:

{
  "name": "Northern Express",
  "origin_station_id": 1,
  "destination_station_id": 2,
  "transport_mode": "train",
  "active": true
}

## Incidents

GET /api/v1/incidents

Supported filters:

- route_id
- station_id
- incident_type
- severity
- status
- from
- to
- min_delay
- limit
- offset

GET /api/v1/incidents/{incident_id}

POST /api/v1/incidents

- Operator or admin

PUT /api/v1/incidents/{incident_id}

- Operator or admin

PATCH /api/v1/incidents/{incident_id}/status

- Operator or admin
- Use to move an incident through open, monitoring, and resolved

DELETE /api/v1/incidents/{incident_id}

- Admin only

Example create request:

{
  "route_id": 1,
  "station_id": 1,
  "incident_type": "delay",
  "severity": "medium",
  "status": "open",
  "title": "Platform congestion",
  "description": "Passenger crowding delayed dispatch by 12 minutes.",
  "delay_minutes": 12,
  "occurred_at": "2026-03-10T07:45:00Z",
  "resolved_at": null
}

Example response:

{
  "id": 1,
  "route_id": 1,
  "station_id": 1,
  "incident_type": "delay",
  "severity": "medium",
  "status": "open",
  "title": "Platform congestion",
  "description": "Passenger crowding delayed dispatch by 12 minutes.",
  "delay_minutes": 12,
  "occurred_at": "2026-03-10T07:45:00Z",
  "resolved_at": null,
  "created_at": "2026-03-17T12:00:00Z",
  "updated_at": "2026-03-17T12:00:00Z"
}

## Analytics

Analytics default to the last 30 days if `from` and `to` are not supplied.

GET /api/v1/analytics/routes/{route_id}/overview

Returns:

- incident_count
- average_delay_minutes
- cancellation_count
- severe_incident_count
- reliability_score

Reliability score is a documented heuristic:

- type weight + severity weight + capped delay contribution per incident
- penalties are averaged across the selected time window
- score is clamped between 0 and 100
- this is an incident-based comparative metric, not an official operator KPI

GET /api/v1/analytics/routes/{route_id}/worst-time

Returns the hour of day with the highest disruption score for a route.

GET /api/v1/analytics/stations/top-delayed

- Query params: limit, from, to
- Returns stations ranked by total delay minutes and incident count

GET /api/v1/analytics/incidents/by-hour

- Query params: from, to
- Returns incident volume and average delay grouped by hour of day

Example analytics response:

{
  "route_id": 1,
  "from_date": "2026-03-10T00:00:00Z",
  "to_date": "2026-03-10T23:59:59Z",
  "incident_count": 3,
  "average_delay_minutes": 26.5,
  "cancellation_count": 1,
  "severe_incident_count": 2,
  "reliability_score": 73.0
}

## OpenAPI And Interactive Docs

FastAPI automatically exposes:

- /docs for Swagger UI
- /openapi.json for the OpenAPI schema

These should be used during development and can also support the coursework demonstration.
