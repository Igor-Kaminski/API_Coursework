from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.database import get_db_session
from app.core.errors import api_error, normalize_lookup_value
from app.core.security import AuthContext, Role, require_roles
from app.models.incident import Incident
from app.models.journey_record import JourneyRecord
from app.models.route import Route
from app.models.station import Station
from app.schemas.route import RouteCreate, RouteRead, RouteUpdate

router = APIRouter(prefix="/routes", tags=["routes"])
DBSession = Annotated[Session, Depends(get_db_session)]
AdminRole = Annotated[AuthContext, Depends(require_roles(Role.ADMIN))]


def validate_station_ids(db: Session, origin_station_id: int, destination_station_id: int) -> None:
    if db.get(Station, origin_station_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "origin station not found")

    if db.get(Station, destination_station_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "destination station not found")


@router.get("", response_model=list[RouteRead])
def list_routes(
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    code: str | None = Query(default=None),
    name: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    destination: str | None = Query(default=None),
    operator_name: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> list[Route]:
    code = normalize_lookup_value(code)
    name = normalize_lookup_value(name)
    origin = normalize_lookup_value(origin)
    destination = normalize_lookup_value(destination)
    operator_name = normalize_lookup_value(operator_name)

    origin_station_alias = aliased(Station)
    destination_station_alias = aliased(Station)
    query = (
        select(Route)
        .options(
            joinedload(Route.origin_station),
            joinedload(Route.destination_station),
        )
    )
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
    return list(db.scalars(query))


@router.get("/code/{route_code}", response_model=RouteRead)
def get_route_by_code(route_code: str, db: DBSession) -> Route:
    route_code = normalize_lookup_value(route_code)
    if route_code is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")

    query = (
        select(Route)
        .options(
            joinedload(Route.origin_station),
            joinedload(Route.destination_station),
        )
        .where(func.lower(Route.code) == route_code.lower())
    )
    route = db.scalar(query)
    if route is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")
    return route


@router.get("/{route_id}", response_model=RouteRead)
def get_route(route_id: int, db: DBSession) -> Route:
    query = (
        select(Route)
        .options(
            joinedload(Route.origin_station),
            joinedload(Route.destination_station),
        )
        .where(Route.id == route_id)
    )
    route = db.scalar(query)
    if route is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")
    return route


@router.post("", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
def create_route(payload: RouteCreate, db: DBSession, _: AdminRole) -> Route:
    validate_station_ids(db, payload.origin_station_id, payload.destination_station_id)

    route = Route(**payload.model_dump())
    db.add(route)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "duplicate route definition") from exc

    refreshed = db.scalar(
        select(Route)
        .options(joinedload(Route.origin_station), joinedload(Route.destination_station))
        .where(Route.id == route.id)
    )
    assert refreshed is not None
    return refreshed


@router.patch("/{route_id}", response_model=RouteRead)
def update_route(
    route_id: int,
    payload: RouteUpdate,
    db: DBSession,
    _: AdminRole,
) -> Route:
    route = db.get(Route, route_id)
    if route is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(route, field, value)

    validate_station_ids(db, route.origin_station_id, route.destination_station_id)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "duplicate route definition") from exc

    refreshed = db.scalar(
        select(Route)
        .options(joinedload(Route.origin_station), joinedload(Route.destination_station))
        .where(Route.id == route.id)
    )
    assert refreshed is not None
    return refreshed


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(route_id: int, db: DBSession, _: AdminRole) -> Response:
    route = db.get(Route, route_id)
    if route is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")

    journey_reference_count = db.scalar(
        select(func.count()).select_from(JourneyRecord).where(JourneyRecord.route_id == route_id)
    ) or 0
    incident_reference_count = db.scalar(
        select(func.count()).select_from(Incident).where(Incident.route_id == route_id)
    ) or 0
    if journey_reference_count or incident_reference_count:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "route cannot be deleted while it is referenced by journey records or incidents",
            details=[
                {
                    "field": "journey_records",
                    "message": f"{journey_reference_count} referencing journey record(s) found",
                },
                {
                    "field": "incidents",
                    "message": f"{incident_reference_count} referencing incident(s) found",
                },
            ],
        )

    db.delete(route)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(
            status.HTTP_409_CONFLICT,
            "route cannot be deleted while it is referenced by journey records or incidents",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
