from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import AuthContext, Role, require_roles
from app.models.station import Station
from app.schemas.station import StationCreate, StationRead, StationUpdate

router = APIRouter(prefix="/stations", tags=["stations"])
DBSession = Annotated[Session, Depends(get_db_session)]
AdminRole = Annotated[AuthContext, Depends(require_roles(Role.ADMIN))]


@router.get("", response_model=list[StationRead])
def list_stations(
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Station]:
    query = select(Station).order_by(Station.name).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.get("/{station_id}", response_model=StationRead)
def get_station(station_id: int, db: DBSession) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="station not found",
        )
    return station


@router.post("", response_model=StationRead, status_code=status.HTTP_201_CREATED)
def create_station(payload: StationCreate, db: DBSession, _: AdminRole) -> Station:
    station = Station(**payload.model_dump())
    db.add(station)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="station with the same code already exists",
        ) from exc

    db.refresh(station)
    return station


@router.patch("/{station_id}", response_model=StationRead)
def update_station(
    station_id: int,
    payload: StationUpdate,
    db: DBSession,
    _: AdminRole,
) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="station not found",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(station, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="station with the same code already exists",
        ) from exc

    db.refresh(station)
    return station


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_station(station_id: int, db: DBSession, _: AdminRole) -> Response:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="station not found",
        )

    db.delete(station)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
