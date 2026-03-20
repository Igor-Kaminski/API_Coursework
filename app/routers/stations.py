from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import api_error, normalize_lookup_value, openapi_error_responses
from app.core.security import AuthContext, Role, require_roles
from app.models.incident import Incident
from app.models.route import Route
from app.models.station import Station
from app.schemas.station import StationCreate, StationRead, StationUpdate

router = APIRouter(prefix="/stations", tags=["stations"])
DBSession = Annotated[Session, Depends(get_db_session)]
AdminRole = Annotated[AuthContext, Depends(require_roles(Role.ADMIN))]


@router.get("", response_model=list[StationRead], responses=openapi_error_responses(422))
def list_stations(
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    code: str | None = Query(default=None),
    name: str | None = Query(default=None),
    city: str | None = Query(default=None),
    crs_code: str | None = Query(default=None),
    tiploc_code: str | None = Query(default=None),
) -> list[Station]:
    code = normalize_lookup_value(code)
    name = normalize_lookup_value(name)
    city = normalize_lookup_value(city)
    crs_code = normalize_lookup_value(crs_code)
    tiploc_code = normalize_lookup_value(tiploc_code)

    query = select(Station)
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
    return list(db.scalars(query))


@router.get("/code/{station_code}", response_model=StationRead, responses=openapi_error_responses(404))
def get_station_by_code(station_code: str, db: DBSession) -> Station:
    station_code = normalize_lookup_value(station_code)
    if station_code is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "station not found")

    station = db.scalar(select(Station).where(func.lower(Station.code) == station_code.lower()))
    if station is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "station not found")
    return station


@router.get("/{station_id}", response_model=StationRead, responses=openapi_error_responses(404))
def get_station(station_id: int, db: DBSession) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "station not found")
    return station


@router.post(
    "",
    response_model=StationRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 409, 422),
)
def create_station(payload: StationCreate, db: DBSession, _: AdminRole) -> Station:
    station = Station(**payload.model_dump())
    db.add(station)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(
            status.HTTP_409_CONFLICT,
            "station with the same code, CRS code, or TIPLOC code already exists",
        ) from exc

    db.refresh(station)
    return station


@router.patch(
    "/{station_id}",
    response_model=StationRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def update_station(
    station_id: int,
    payload: StationUpdate,
    db: DBSession,
    _: AdminRole,
) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "station not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(station, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(
            status.HTTP_409_CONFLICT,
            "station with the same code, CRS code, or TIPLOC code already exists",
        ) from exc

    db.refresh(station)
    return station


@router.delete(
    "/{station_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=openapi_error_responses(401, 403, 404, 409),
)
def delete_station(station_id: int, db: DBSession, _: AdminRole) -> Response:
    station = db.get(Station, station_id)
    if station is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "station not found")

    route_reference_count = db.scalar(
        select(func.count())
        .select_from(Route)
        .where((Route.origin_station_id == station_id) | (Route.destination_station_id == station_id))
    ) or 0
    incident_reference_count = db.scalar(
        select(func.count()).select_from(Incident).where(Incident.station_id == station_id)
    ) or 0
    if route_reference_count or incident_reference_count:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "station cannot be deleted while it is referenced by routes or incidents",
            details=[
                {"field": "routes", "message": f"{route_reference_count} referencing route(s) found"},
                {
                    "field": "incidents",
                    "message": f"{incident_reference_count} referencing incident(s) found",
                },
            ],
        )

    db.delete(station)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(
            status.HTTP_409_CONFLICT,
            "station cannot be deleted while it is referenced by routes or incidents",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
