from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DBSession
from app.core.exceptions import ConflictError
from app.models import Incident, Route, Station
from app.schemas.station import StationCreate, StationRead, StationUpdate
from app.services.incident_service import get_station_or_404


router = APIRouter()


@router.get("", response_model=list[StationRead], summary="List stations")
def list_stations(
    db: DBSession,
    city: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Station]:
    stmt = select(Station).order_by(Station.city.asc(), Station.name.asc()).offset(offset).limit(limit)
    if city:
        stmt = stmt.where(Station.city.ilike(f"%{city}%"))
    return db.scalars(stmt).all()


@router.get("/{station_id}", response_model=StationRead, summary="Get station")
def get_station(station_id: int, db: DBSession) -> Station:
    return get_station_or_404(db, station_id)


@router.post("", response_model=StationRead, status_code=status.HTTP_201_CREATED, summary="Create station")
def create_station(payload: StationCreate, db: DBSession, _: AdminUser) -> Station:
    station = Station(**payload.model_dump())
    db.add(station)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A station with the same code or name/city already exists.") from exc
    db.refresh(station)
    return station


@router.put("/{station_id}", response_model=StationRead, summary="Update station")
def update_station(station_id: int, payload: StationUpdate, db: DBSession, _: AdminUser) -> Station:
    station = get_station_or_404(db, station_id)
    for field, value in payload.model_dump().items():
        setattr(station, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A station with the same code or name/city already exists.") from exc
    db.refresh(station)
    return station


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete station")
def delete_station(station_id: int, db: DBSession, _: AdminUser) -> Response:
    station = get_station_or_404(db, station_id)
    route_count = db.scalar(
        select(func.count(Route.id)).where(
            or_(Route.origin_station_id == station_id, Route.destination_station_id == station_id)
        )
    )
    incident_count = db.scalar(select(func.count(Incident.id)).where(Incident.station_id == station_id))
    if route_count or incident_count:
        raise ConflictError("Station cannot be deleted while it is referenced by routes or incidents.")

    db.delete(station)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
