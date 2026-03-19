from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.database import SessionLocal
from app.core.security import Role
from app.mcp.auth import require_api_role
from app.models.incident import Incident
from app.models.journey_record import JourneyRecord
from app.models.route import Route
from app.models.station import Station
from app.services.analytics_service import AnalyticsService

SessionFactory = SessionLocal
analytics_service = AnalyticsService()


class StationWriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    crs_code: str | None = Field(default=None, max_length=3)
    tiploc_code: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class StationUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=32)
    crs_code: str | None = Field(default=None, max_length=3)
    tiploc_code: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class RouteWriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_station_id: int
    destination_station_id: int
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    operator_name: str | None = Field(default=None, max_length=255)
    distance_km: Decimal | None = None
    is_active: bool = True


class RouteUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_station_id: int | None = None
    destination_station_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    operator_name: str | None = Field(default=None, max_length=255)
    distance_km: Decimal | None = None
    is_active: bool | None = None


class IncidentWriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: int | None = None
    station_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    incident_type: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=50)
    status: str = Field(default="open", min_length=1, max_length=50)
    reported_at: datetime


class IncidentUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: int | None = None
    station_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    incident_type: str | None = Field(default=None, min_length=1, max_length=100)
    severity: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, min_length=1, max_length=50)
    reported_at: datetime | None = None


@contextmanager
def db_session() -> Any:
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json_compatible(item) for key, item in value.items()}
    return value


def _dump_model(model: BaseModel) -> dict[str, Any]:
    return _to_json_compatible(model.model_dump(mode="python"))


def _serialize_station(station: Station) -> dict[str, Any]:
    return {
        "id": station.id,
        "name": station.name,
        "code": station.code,
        "crs_code": station.crs_code,
        "tiploc_code": station.tiploc_code,
        "city": station.city,
        "latitude": _to_json_compatible(station.latitude),
        "longitude": _to_json_compatible(station.longitude),
        "created_at": station.created_at.isoformat(),
        "updated_at": station.updated_at.isoformat(),
    }


def _serialize_route(route: Route) -> dict[str, Any]:
    return {
        "id": route.id,
        "origin_station_id": route.origin_station_id,
        "destination_station_id": route.destination_station_id,
        "name": route.name,
        "code": route.code,
        "operator_name": route.operator_name,
        "distance_km": _to_json_compatible(route.distance_km),
        "is_active": route.is_active,
        "origin_station": _serialize_station(route.origin_station),
        "destination_station": _serialize_station(route.destination_station),
        "created_at": route.created_at.isoformat(),
        "updated_at": route.updated_at.isoformat(),
    }


def _serialize_incident(incident: Incident) -> dict[str, Any]:
    return {
        "id": incident.id,
        "route_id": incident.route_id,
        "station_id": incident.station_id,
        "title": incident.title,
        "description": incident.description,
        "incident_type": incident.incident_type,
        "severity": incident.severity,
        "status": incident.status,
        "reported_at": incident.reported_at.isoformat(),
        "created_at": incident.created_at.isoformat(),
        "updated_at": incident.updated_at.isoformat(),
    }


def _validate_station_ids(db: Session, origin_station_id: int, destination_station_id: int) -> None:
    if db.get(Station, origin_station_id) is None:
        raise ValueError("origin station not found")
    if db.get(Station, destination_station_id) is None:
        raise ValueError("destination station not found")


def _validate_incident_scope(
    db: Session,
    route_id: int | None,
    station_id: int | None,
) -> None:
    if route_id is None and station_id is None:
        raise ValueError("either route_id or station_id must be provided")
    if route_id is not None and db.get(Route, route_id) is None:
        raise ValueError("route not found")
    if station_id is not None and db.get(Station, station_id) is None:
        raise ValueError("station not found")


def _get_station_query() -> Any:
    return select(Station)


def _get_route_query() -> Any:
    return select(Route).options(
        joinedload(Route.origin_station),
        joinedload(Route.destination_station),
    )


def _fetch_station(
    db: Session,
    station_id: int | None = None,
    code: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
) -> Station:
    if station_id is not None:
        station = db.get(Station, station_id)
        if station is None:
            raise ValueError("station not found")
        return station

    query = _get_station_query()
    if code:
        query = query.where(func.lower(Station.code) == code.lower())
    elif crs_code:
        query = query.where(func.lower(Station.crs_code) == crs_code.lower())
    elif tiploc_code:
        query = query.where(func.lower(Station.tiploc_code) == tiploc_code.lower())
    else:
        raise ValueError("provide station_id, code, crs_code, or tiploc_code")

    station = db.scalar(query)
    if station is None:
        raise ValueError("station not found")
    return station


def _fetch_route(
    db: Session,
    route_id: int | None = None,
    code: str | None = None,
) -> Route:
    if route_id is not None:
        route = db.scalar(_get_route_query().where(Route.id == route_id))
        if route is None:
            raise ValueError("route not found")
        return route

    if not code:
        raise ValueError("provide route_id or code")

    route = db.scalar(_get_route_query().where(func.lower(Route.code) == code.lower()))
    if route is None:
        raise ValueError("route not found")
    return route


def search_stations_impl(
    *,
    limit: int = 20,
    offset: int = 0,
    code: str | None = None,
    name: str | None = None,
    city: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
) -> list[dict[str, Any]]:
    with db_session() as db:
        query = _get_station_query()
        if code:
            query = query.where(func.lower(Station.code) == code.lower())
        if name:
            query = query.where(func.lower(Station.name).contains(name.lower()))
        if city:
            query = query.where(func.lower(Station.city).contains(city.lower()))
        if crs_code:
            query = query.where(func.lower(Station.crs_code) == crs_code.lower())
        if tiploc_code:
            query = query.where(func.lower(Station.tiploc_code) == tiploc_code.lower())
        query = query.order_by(Station.name).limit(limit).offset(offset)
        return [_serialize_station(station) for station in db.scalars(query)]


def get_station_impl(
    *,
    station_id: int | None = None,
    code: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
) -> dict[str, Any]:
    with db_session() as db:
        return _serialize_station(
            _fetch_station(
                db,
                station_id=station_id,
                code=code,
                crs_code=crs_code,
                tiploc_code=tiploc_code,
            )
        )


def search_routes_impl(
    *,
    limit: int = 20,
    offset: int = 0,
    code: str | None = None,
    name: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    operator_name: str | None = None,
    is_active: bool | None = None,
) -> list[dict[str, Any]]:
    with db_session() as db:
        origin_station_alias = aliased(Station)
        destination_station_alias = aliased(Station)
        query = _get_route_query()
        if code:
            query = query.where(func.lower(Route.code) == code.lower())
        if name:
            query = query.where(func.lower(Route.name).contains(name.lower()))
        if operator_name:
            query = query.where(func.lower(Route.operator_name) == operator_name.lower())
        if is_active is not None:
            query = query.where(Route.is_active == is_active)
        if origin:
            query = query.join(origin_station_alias, Route.origin_station).where(
                or_(
                    func.lower(origin_station_alias.code) == origin.lower(),
                    func.lower(origin_station_alias.crs_code) == origin.lower(),
                    func.lower(origin_station_alias.tiploc_code) == origin.lower(),
                )
            )
        if destination:
            query = query.join(destination_station_alias, Route.destination_station).where(
                or_(
                    func.lower(destination_station_alias.code) == destination.lower(),
                    func.lower(destination_station_alias.crs_code) == destination.lower(),
                    func.lower(destination_station_alias.tiploc_code) == destination.lower(),
                )
            )
        query = query.order_by(Route.name).limit(limit).offset(offset)
        return [_serialize_route(route) for route in db.scalars(query)]


def get_route_impl(
    *,
    route_id: int | None = None,
    code: str | None = None,
) -> dict[str, Any]:
    with db_session() as db:
        return _serialize_route(_fetch_route(db, route_id=route_id, code=code))


def list_incidents_impl(
    *,
    limit: int = 20,
    offset: int = 0,
    route_id: int | None = None,
    station_id: int | None = None,
    incident_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    reported_from: datetime | None = None,
    reported_to: datetime | None = None,
) -> list[dict[str, Any]]:
    with db_session() as db:
        query = select(Incident)
        if route_id is not None:
            query = query.where(Incident.route_id == route_id)
        if station_id is not None:
            query = query.where(Incident.station_id == station_id)
        if incident_type:
            query = query.where(func.lower(Incident.incident_type) == incident_type.lower())
        if severity:
            query = query.where(func.lower(Incident.severity) == severity.lower())
        if status:
            query = query.where(func.lower(Incident.status) == status.lower())
        if reported_from:
            query = query.where(Incident.reported_at >= reported_from)
        if reported_to:
            query = query.where(Incident.reported_at <= reported_to)
        query = query.order_by(Incident.reported_at.desc()).limit(limit).offset(offset)
        return [_serialize_incident(incident) for incident in db.scalars(query)]


def get_incident_impl(incident_id: int) -> dict[str, Any]:
    with db_session() as db:
        incident = db.get(Incident, incident_id)
        if incident is None:
            raise ValueError("incident not found")
        return _serialize_incident(incident)


def get_route_reliability_impl(
    *,
    route_id: int | None = None,
    route_code: str | None = None,
) -> dict[str, Any]:
    with db_session() as db:
        route = _fetch_route(db, route_id=route_id, code=route_code)
        return _dump_model(analytics_service.get_route_reliability(db, route.id))


def get_route_average_delay_impl(
    *,
    route_id: int | None = None,
    route_code: str | None = None,
) -> dict[str, Any]:
    with db_session() as db:
        route = _fetch_route(db, route_id=route_id, code=route_code)
        return _dump_model(analytics_service.get_route_average_delay(db, route.id))


def get_hourly_delay_patterns_impl() -> list[dict[str, Any]]:
    with db_session() as db:
        return [
            _dump_model(point) for point in analytics_service.get_hourly_delay_patterns(db)
        ]


def get_daily_delay_patterns_impl() -> list[dict[str, Any]]:
    with db_session() as db:
        return [_dump_model(point) for point in analytics_service.get_daily_delay_patterns(db)]


def get_station_hotspots_impl(limit: int = 10) -> list[dict[str, Any]]:
    with db_session() as db:
        return [_dump_model(item) for item in analytics_service.get_station_hotspots(db, limit)]


def get_incident_frequency_impl() -> list[dict[str, Any]]:
    with db_session() as db:
        return [_dump_model(item) for item in analytics_service.get_incident_frequency(db)]


def get_common_delay_reasons_impl(limit: int = 10) -> list[dict[str, Any]]:
    with db_session() as db:
        return [_dump_model(item) for item in analytics_service.get_common_delay_reasons(db, limit)]


def get_route_name_coverage_impl(limit: int = 10) -> dict[str, Any]:
    with db_session() as db:
        return _dump_model(analytics_service.get_route_name_coverage(db, limit))


def create_station_impl(
    *,
    api_key: str,
    name: str,
    code: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
    city: str | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN)
    payload = StationWriteInput(
        name=name,
        code=code,
        crs_code=crs_code,
        tiploc_code=tiploc_code,
        city=city,
        latitude=latitude,
        longitude=longitude,
    )

    with db_session() as db:
        station = Station(**payload.model_dump())
        db.add(station)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                "station with the same code, CRS code, or TIPLOC code already exists"
            ) from exc
        db.refresh(station)
        return {"success": True, "station": _serialize_station(station)}


def update_station_impl(
    *,
    api_key: str,
    station_id: int,
    name: str | None = None,
    code: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
    city: str | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN)
    payload = StationUpdateInput(
        name=name,
        code=code,
        crs_code=crs_code,
        tiploc_code=tiploc_code,
        city=city,
        latitude=latitude,
        longitude=longitude,
    )

    with db_session() as db:
        station = db.get(Station, station_id)
        if station is None:
            raise ValueError("station not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(station, field, value)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                "station with the same code, CRS code, or TIPLOC code already exists"
            ) from exc
        db.refresh(station)
        return {"success": True, "station": _serialize_station(station)}


def delete_station_impl(*, api_key: str, station_id: int) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN)

    with db_session() as db:
        station = db.get(Station, station_id)
        if station is None:
            raise ValueError("station not found")
        db.delete(station)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                "station cannot be deleted while referenced by routes or incidents"
            ) from exc
        return {"success": True, "deleted_station_id": station_id}


def create_route_impl(
    *,
    api_key: str,
    origin_station_id: int,
    destination_station_id: int,
    name: str,
    code: str | None = None,
    operator_name: str | None = None,
    distance_km: Decimal | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN)
    payload = RouteWriteInput(
        origin_station_id=origin_station_id,
        destination_station_id=destination_station_id,
        name=name,
        code=code,
        operator_name=operator_name,
        distance_km=distance_km,
        is_active=is_active,
    )

    with db_session() as db:
        _validate_station_ids(db, payload.origin_station_id, payload.destination_station_id)
        route = Route(**payload.model_dump())
        db.add(route)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("duplicate route definition") from exc
        refreshed = db.scalar(_get_route_query().where(Route.id == route.id))
        assert refreshed is not None
        return {"success": True, "route": _serialize_route(refreshed)}


def update_route_impl(
    *,
    api_key: str,
    route_id: int,
    origin_station_id: int | None = None,
    destination_station_id: int | None = None,
    name: str | None = None,
    code: str | None = None,
    operator_name: str | None = None,
    distance_km: Decimal | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN)
    payload = RouteUpdateInput(
        origin_station_id=origin_station_id,
        destination_station_id=destination_station_id,
        name=name,
        code=code,
        operator_name=operator_name,
        distance_km=distance_km,
        is_active=is_active,
    )

    with db_session() as db:
        route = db.get(Route, route_id)
        if route is None:
            raise ValueError("route not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(route, field, value)
        _validate_station_ids(db, route.origin_station_id, route.destination_station_id)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("duplicate route definition") from exc
        refreshed = db.scalar(_get_route_query().where(Route.id == route.id))
        assert refreshed is not None
        return {"success": True, "route": _serialize_route(refreshed)}


def delete_route_impl(*, api_key: str, route_id: int) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN)

    with db_session() as db:
        route = db.get(Route, route_id)
        if route is None:
            raise ValueError("route not found")
        db.delete(route)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                "route cannot be deleted while referenced by journey records or incidents"
            ) from exc
        return {"success": True, "deleted_route_id": route_id}


def create_incident_impl(
    *,
    api_key: str,
    title: str,
    description: str,
    incident_type: str,
    severity: str,
    reported_at: datetime,
    route_id: int | None = None,
    station_id: int | None = None,
    status: str = "open",
) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN, Role.OPERATOR, Role.USER)
    payload = IncidentWriteInput(
        route_id=route_id,
        station_id=station_id,
        title=title,
        description=description,
        incident_type=incident_type,
        severity=severity,
        status=status,
        reported_at=reported_at,
    )

    with db_session() as db:
        _validate_incident_scope(db, payload.route_id, payload.station_id)
        incident = Incident(**payload.model_dump())
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return {"success": True, "incident": _serialize_incident(incident)}


def update_incident_impl(
    *,
    api_key: str,
    incident_id: int,
    route_id: int | None = None,
    station_id: int | None = None,
    title: str | None = None,
    description: str | None = None,
    incident_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    reported_at: datetime | None = None,
) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN, Role.OPERATOR)
    payload = IncidentUpdateInput(
        route_id=route_id,
        station_id=station_id,
        title=title,
        description=description,
        incident_type=incident_type,
        severity=severity,
        status=status,
        reported_at=reported_at,
    )

    with db_session() as db:
        incident = db.get(Incident, incident_id)
        if incident is None:
            raise ValueError("incident not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(incident, field, value)
        _validate_incident_scope(db, incident.route_id, incident.station_id)
        db.commit()
        db.refresh(incident)
        return {"success": True, "incident": _serialize_incident(incident)}


def delete_incident_impl(*, api_key: str, incident_id: int) -> dict[str, Any]:
    require_api_role(api_key, Role.ADMIN, Role.OPERATOR)

    with db_session() as db:
        incident = db.get(Incident, incident_id)
        if incident is None:
            raise ValueError("incident not found")
        db.delete(incident)
        db.commit()
        return {"success": True, "deleted_incident_id": incident_id}


def get_data_coverage_impl() -> dict[str, Any]:
    with db_session() as db:
        station_count = db.scalar(select(func.count()).select_from(Station)) or 0
        route_count = db.scalar(select(func.count()).select_from(Route)) or 0
        incident_count = db.scalar(select(func.count()).select_from(Incident)) or 0
        journey_count = db.scalar(select(func.count()).select_from(JourneyRecord)) or 0
        city_count = db.scalar(
            select(func.count()).select_from(Station).where(Station.city.is_not(None))
        ) or 0
        crs_count = db.scalar(
            select(func.count()).select_from(Station).where(Station.crs_code.is_not(None))
        ) or 0
        tiploc_count = db.scalar(
            select(func.count()).select_from(Station).where(Station.tiploc_code.is_not(None))
        ) or 0
        coordinate_count = db.scalar(
            select(func.count())
            .select_from(Station)
            .where(Station.latitude.is_not(None), Station.longitude.is_not(None))
        ) or 0
        distance_count = db.scalar(
            select(func.count()).select_from(Route).where(Route.distance_km.is_not(None))
        ) or 0
        route_name_coverage = _dump_model(analytics_service.get_route_name_coverage(db, 10))

    return {
        "stations": station_count,
        "routes": route_count,
        "journey_records": journey_count,
        "incidents": incident_count,
        "station_city_coverage": city_count,
        "station_crs_coverage": crs_count,
        "station_tiploc_coverage": tiploc_count,
        "station_coordinate_coverage": coordinate_count,
        "route_distance_coverage": distance_count,
        "route_name_coverage": route_name_coverage,
    }


def _json_resource(payload: dict[str, Any]) -> str:
    return json.dumps(_to_json_compatible(payload), indent=2, sort_keys=True)


mcp = FastMCP(
    name="Rail Reliability MCP",
    instructions=(
        "Use these tools to inspect and administer UK rail reference, incident, and "
        "analytics data stored locally in PostgreSQL. Read tools are public. "
        "Station and route write tools require the admin API key. Incident creation "
        "accepts user, operator, or admin keys; incident updates and deletes require "
        "operator or admin keys."
    ),
    dependencies=["mcp", "sqlalchemy", "psycopg[binary]", "pydantic"],
)


@mcp.resource(
    "rail://overview",
    name="Project overview",
    mime_type="application/json",
)
def overview_resource() -> str:
    return _json_resource(
        {
            "project": "Rail Reliability API",
            "transport_modes": ["rail"],
            "database_backing": "PostgreSQL via SQLAlchemy",
            "public_domains": ["stations", "routes", "incidents", "analytics"],
            "advanced_feature": "MCP server with read and guarded write tools",
        }
    )


@mcp.resource(
    "rail://auth-model",
    name="Auth model",
    mime_type="application/json",
)
def auth_model_resource() -> str:
    return _json_resource(
        {
            "read_tools": "No API key required",
            "station_route_writes": "admin API key required",
            "incident_create": "user, operator, or admin API key required",
            "incident_update_delete": "operator or admin API key required",
            "api_key_parameter": "Mutating tools accept an api_key argument",
        }
    )


@mcp.resource(
    "rail://data-coverage",
    name="Current data coverage",
    mime_type="application/json",
)
def data_coverage_resource() -> str:
    return _json_resource(get_data_coverage_impl())


@mcp.resource(
    "rail://tool-guide",
    name="Tool guide",
    mime_type="application/json",
)
def tool_guide_resource() -> str:
    return _json_resource(
        {
            "lookup_tools": [
                "search_stations",
                "get_station",
                "search_routes",
                "get_route",
                "list_incidents",
                "get_incident",
            ],
            "analytics_tools": [
                "get_route_reliability",
                "get_route_average_delay",
                "get_hourly_delay_patterns",
                "get_daily_delay_patterns",
                "get_station_hotspots",
                "get_incident_frequency",
                "get_common_delay_reasons",
                "get_route_name_coverage",
            ],
            "write_tools": [
                "create_station",
                "update_station",
                "delete_station",
                "create_route",
                "update_route",
                "delete_route",
                "create_incident",
                "update_incident",
                "delete_incident",
            ],
        }
    )


@mcp.prompt(
    name="investigate_route_delay",
    description="Guide an MCP client through route delay analysis.",
)
def investigate_route_delay_prompt(route_code: str) -> str:
    return (
        f"Investigate performance for route `{route_code}`. First call `get_route` "
        f"with `code={route_code}` to confirm the route. Then call "
        "`get_route_reliability` and `get_route_average_delay` with the same route "
        "identifier. If the route appears problematic, compare it with "
        "`get_hourly_delay_patterns`, `get_daily_delay_patterns`, "
        "`get_common_delay_reasons`, and `list_incidents` filtered to the route."
    )


@mcp.prompt(
    name="triage_recent_incidents",
    description="Guide an MCP client through incident triage.",
)
def triage_recent_incidents_prompt(severity: str = "high") -> str:
    return (
        f"Review recent `{severity}` severity incidents. Use `list_incidents` filtered "
        f"by `severity={severity}` and an appropriate recent `reported_from` value. "
        "For each important case, call `get_incident`, then cross-check the linked "
        "route with `get_route` and the route analytics tools."
    )


@mcp.tool(name="search_stations", description="Search stations by code, name, city, CRS, or TIPLOC.", structured_output=True)
def search_stations(
    limit: int = 20,
    offset: int = 0,
    code: str | None = None,
    name: str | None = None,
    city: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
) -> list[dict[str, Any]]:
    return search_stations_impl(
        limit=limit,
        offset=offset,
        code=code,
        name=name,
        city=city,
        crs_code=crs_code,
        tiploc_code=tiploc_code,
    )


@mcp.tool(name="get_station", description="Get a single station by id or reference code.", structured_output=True)
def get_station(
    station_id: int | None = None,
    code: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
) -> dict[str, Any]:
    return get_station_impl(
        station_id=station_id,
        code=code,
        crs_code=crs_code,
        tiploc_code=tiploc_code,
    )


@mcp.tool(name="create_station", description="Create a station reference record with an admin API key.", structured_output=True)
def create_station(
    api_key: str,
    name: str,
    code: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
    city: str | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> dict[str, Any]:
    return create_station_impl(
        api_key=api_key,
        name=name,
        code=code,
        crs_code=crs_code,
        tiploc_code=tiploc_code,
        city=city,
        latitude=latitude,
        longitude=longitude,
    )


@mcp.tool(name="update_station", description="Update a station reference record with an admin API key.", structured_output=True)
def update_station(
    api_key: str,
    station_id: int,
    name: str | None = None,
    code: str | None = None,
    crs_code: str | None = None,
    tiploc_code: str | None = None,
    city: str | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> dict[str, Any]:
    return update_station_impl(
        api_key=api_key,
        station_id=station_id,
        name=name,
        code=code,
        crs_code=crs_code,
        tiploc_code=tiploc_code,
        city=city,
        latitude=latitude,
        longitude=longitude,
    )


@mcp.tool(name="delete_station", description="Delete a station reference record with an admin API key.", structured_output=True)
def delete_station(api_key: str, station_id: int) -> dict[str, Any]:
    return delete_station_impl(api_key=api_key, station_id=station_id)


@mcp.tool(name="search_routes", description="Search routes by code, name, origin, destination, operator, or active state.", structured_output=True)
def search_routes(
    limit: int = 20,
    offset: int = 0,
    code: str | None = None,
    name: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    operator_name: str | None = None,
    is_active: bool | None = None,
) -> list[dict[str, Any]]:
    return search_routes_impl(
        limit=limit,
        offset=offset,
        code=code,
        name=name,
        origin=origin,
        destination=destination,
        operator_name=operator_name,
        is_active=is_active,
    )


@mcp.tool(name="get_route", description="Get a single route by id or public route code.", structured_output=True)
def get_route(route_id: int | None = None, code: str | None = None) -> dict[str, Any]:
    return get_route_impl(route_id=route_id, code=code)


@mcp.tool(name="create_route", description="Create a route reference record with an admin API key.", structured_output=True)
def create_route(
    api_key: str,
    origin_station_id: int,
    destination_station_id: int,
    name: str,
    code: str | None = None,
    operator_name: str | None = None,
    distance_km: Decimal | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    return create_route_impl(
        api_key=api_key,
        origin_station_id=origin_station_id,
        destination_station_id=destination_station_id,
        name=name,
        code=code,
        operator_name=operator_name,
        distance_km=distance_km,
        is_active=is_active,
    )


@mcp.tool(name="update_route", description="Update a route reference record with an admin API key.", structured_output=True)
def update_route(
    api_key: str,
    route_id: int,
    origin_station_id: int | None = None,
    destination_station_id: int | None = None,
    name: str | None = None,
    code: str | None = None,
    operator_name: str | None = None,
    distance_km: Decimal | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    return update_route_impl(
        api_key=api_key,
        route_id=route_id,
        origin_station_id=origin_station_id,
        destination_station_id=destination_station_id,
        name=name,
        code=code,
        operator_name=operator_name,
        distance_km=distance_km,
        is_active=is_active,
    )


@mcp.tool(name="delete_route", description="Delete a route reference record with an admin API key.", structured_output=True)
def delete_route(api_key: str, route_id: int) -> dict[str, Any]:
    return delete_route_impl(api_key=api_key, route_id=route_id)


@mcp.tool(name="list_incidents", description="List incidents with optional filters.", structured_output=True)
def list_incidents(
    limit: int = 20,
    offset: int = 0,
    route_id: int | None = None,
    station_id: int | None = None,
    incident_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    reported_from: datetime | None = None,
    reported_to: datetime | None = None,
) -> list[dict[str, Any]]:
    return list_incidents_impl(
        limit=limit,
        offset=offset,
        route_id=route_id,
        station_id=station_id,
        incident_type=incident_type,
        severity=severity,
        status=status,
        reported_from=reported_from,
        reported_to=reported_to,
    )


@mcp.tool(name="get_incident", description="Get a single incident by id.", structured_output=True)
def get_incident(incident_id: int) -> dict[str, Any]:
    return get_incident_impl(incident_id)


@mcp.tool(name="create_incident", description="Create an incident with a user, operator, or admin API key.", structured_output=True)
def create_incident(
    api_key: str,
    title: str,
    description: str,
    incident_type: str,
    severity: str,
    reported_at: datetime,
    route_id: int | None = None,
    station_id: int | None = None,
    status: str = "open",
) -> dict[str, Any]:
    return create_incident_impl(
        api_key=api_key,
        title=title,
        description=description,
        incident_type=incident_type,
        severity=severity,
        reported_at=reported_at,
        route_id=route_id,
        station_id=station_id,
        status=status,
    )


@mcp.tool(name="update_incident", description="Update an incident with an operator or admin API key.", structured_output=True)
def update_incident(
    api_key: str,
    incident_id: int,
    route_id: int | None = None,
    station_id: int | None = None,
    title: str | None = None,
    description: str | None = None,
    incident_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    reported_at: datetime | None = None,
) -> dict[str, Any]:
    return update_incident_impl(
        api_key=api_key,
        incident_id=incident_id,
        route_id=route_id,
        station_id=station_id,
        title=title,
        description=description,
        incident_type=incident_type,
        severity=severity,
        status=status,
        reported_at=reported_at,
    )


@mcp.tool(name="delete_incident", description="Delete an incident with an operator or admin API key.", structured_output=True)
def delete_incident(api_key: str, incident_id: int) -> dict[str, Any]:
    return delete_incident_impl(api_key=api_key, incident_id=incident_id)


@mcp.tool(name="get_route_reliability", description="Compute the route on-time, delayed, and cancelled percentages.", structured_output=True)
def get_route_reliability(
    route_id: int | None = None,
    route_code: str | None = None,
) -> dict[str, Any]:
    return get_route_reliability_impl(route_id=route_id, route_code=route_code)


@mcp.tool(name="get_route_average_delay", description="Compute the average delay for a route.", structured_output=True)
def get_route_average_delay(
    route_id: int | None = None,
    route_code: str | None = None,
) -> dict[str, Any]:
    return get_route_average_delay_impl(route_id=route_id, route_code=route_code)


@mcp.tool(name="get_hourly_delay_patterns", description="Summarize average delays by scheduled departure hour.", structured_output=True)
def get_hourly_delay_patterns() -> list[dict[str, Any]]:
    return get_hourly_delay_patterns_impl()


@mcp.tool(name="get_daily_delay_patterns", description="Summarize average delays by day of week.", structured_output=True)
def get_daily_delay_patterns() -> list[dict[str, Any]]:
    return get_daily_delay_patterns_impl()


@mcp.tool(name="get_station_hotspots", description="Return the most delay-affected stations.", structured_output=True)
def get_station_hotspots(limit: int = 10) -> list[dict[str, Any]]:
    return get_station_hotspots_impl(limit=limit)


@mcp.tool(name="get_incident_frequency", description="Summarize incident counts over time.", structured_output=True)
def get_incident_frequency() -> list[dict[str, Any]]:
    return get_incident_frequency_impl()


@mcp.tool(name="get_common_delay_reasons", description="Return the most common imported delay reasons.", structured_output=True)
def get_common_delay_reasons(limit: int = 10) -> list[dict[str, Any]]:
    return get_common_delay_reasons_impl(limit=limit)


@mcp.tool(name="get_route_name_coverage", description="Summarize how many routes have fully resolved human-readable station names.", structured_output=True)
def get_route_name_coverage(limit: int = 10) -> dict[str, Any]:
    return get_route_name_coverage_impl(limit=limit)


@mcp.tool(name="get_data_coverage", description="Return current database coverage counts and enrichment metrics.", structured_output=True)
def get_data_coverage() -> dict[str, Any]:
    return get_data_coverage_impl()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Rail Reliability MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="MCP transport to use.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE or streamable HTTP transports.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for SSE or streamable HTTP transports.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.transport != "stdio":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(args.transport)


if __name__ == "__main__":
    main()
