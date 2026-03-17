from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DBSession
from app.core.exceptions import ConflictError
from app.models import Incident, Route
from app.models.enums import TransportMode
from app.schemas.route import RouteCreate, RouteRead, RouteUpdate
from app.services.incident_service import get_route_or_404, get_station_or_404


router = APIRouter()


@router.get("", response_model=list[RouteRead], summary="List routes")
def list_routes(
    db: DBSession,
    transport_mode: TransportMode | None = Query(default=None),
    origin_station_id: int | None = Query(default=None, gt=0),
    destination_station_id: int | None = Query(default=None, gt=0),
    active: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Route]:
    stmt = select(Route).order_by(Route.name.asc()).offset(offset).limit(limit)
    if transport_mode is not None:
        stmt = stmt.where(Route.transport_mode == transport_mode)
    if origin_station_id is not None:
        stmt = stmt.where(Route.origin_station_id == origin_station_id)
    if destination_station_id is not None:
        stmt = stmt.where(Route.destination_station_id == destination_station_id)
    if active is not None:
        stmt = stmt.where(Route.active == active)
    return db.scalars(stmt).all()


@router.get("/{route_id}", response_model=RouteRead, summary="Get route")
def get_route(route_id: int, db: DBSession) -> Route:
    return get_route_or_404(db, route_id)


@router.post("", response_model=RouteRead, status_code=status.HTTP_201_CREATED, summary="Create route")
def create_route(payload: RouteCreate, db: DBSession, _: AdminUser) -> Route:
    get_station_or_404(db, payload.origin_station_id)
    get_station_or_404(db, payload.destination_station_id)

    route = Route(**payload.model_dump())
    db.add(route)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A route with the same name and endpoints already exists.") from exc
    db.refresh(route)
    return route


@router.put("/{route_id}", response_model=RouteRead, summary="Update route")
def update_route(route_id: int, payload: RouteUpdate, db: DBSession, _: AdminUser) -> Route:
    route = get_route_or_404(db, route_id)
    get_station_or_404(db, payload.origin_station_id)
    get_station_or_404(db, payload.destination_station_id)

    for field, value in payload.model_dump().items():
        setattr(route, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A route with the same name and endpoints already exists.") from exc
    db.refresh(route)
    return route


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete route")
def delete_route(route_id: int, db: DBSession, _: AdminUser) -> Response:
    route = get_route_or_404(db, route_id)
    incident_count = db.scalar(select(func.count(Incident.id)).where(Incident.route_id == route_id))
    if incident_count:
        raise ConflictError("Route cannot be deleted while incidents reference it.")

    db.delete(route)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
