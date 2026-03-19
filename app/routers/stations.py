from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.station import Station
from app.schemas.station import StationRead

router = APIRouter(prefix="/stations", tags=["stations"])
DBSession = Annotated[Session, Depends(get_db_session)]


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
