from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.incident import Incident
from app.models.route import Route
from app.models.station import Station
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentUpdate

router = APIRouter(prefix="/incidents", tags=["incidents"])
DBSession = Annotated[Session, Depends(get_db_session)]


def validate_related_entities(db: Session, route_id: int | None, station_id: int | None) -> None:
    if route_id is None and station_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="either route_id or station_id must be provided",
        )

    if route_id is not None and db.get(Route, route_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="route not found",
        )

    if station_id is not None and db.get(Station, station_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="station not found",
        )


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Incident]:
    query = select(Incident).order_by(Incident.reported_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: DBSession) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident not found",
        )
    return incident


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: DBSession) -> Incident:
    validate_related_entities(db, payload.route_id, payload.station_id)

    incident = Incident(**payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident(incident_id: int, payload: IncidentUpdate, db: DBSession) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident not found",
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(incident, field, value)

    validate_related_entities(db, incident.route_id, incident.station_id)

    db.commit()
    db.refresh(incident)
    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, db: DBSession) -> Response:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident not found",
        )

    db.delete(incident)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
