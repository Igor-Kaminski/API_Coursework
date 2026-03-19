from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import api_error, normalize_lookup_value, validate_datetime_range
from app.core.security import AuthContext, Role, require_roles
from app.models.incident import Incident
from app.models.route import Route
from app.models.station import Station
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentUpdate

router = APIRouter(prefix="/incidents", tags=["incidents"])
DBSession = Annotated[Session, Depends(get_db_session)]
AuthenticatedRole = Annotated[
    AuthContext,
    Depends(require_roles(Role.ADMIN, Role.OPERATOR, Role.USER)),
]
OperatorRole = Annotated[
    AuthContext,
    Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
]


def validate_related_entities(db: Session, route_id: int | None, station_id: int | None) -> None:
    if route_id is None and station_id is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "either route_id or station_id must be provided",
        )

    if route_id is not None and db.get(Route, route_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")

    if station_id is not None and db.get(Station, station_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "station not found")


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    route_id: int | None = Query(default=None),
    station_id: int | None = Query(default=None),
    incident_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    reported_from: datetime | None = Query(default=None),
    reported_to: datetime | None = Query(default=None),
) -> list[Incident]:
    incident_type = normalize_lookup_value(incident_type)
    severity = normalize_lookup_value(severity)
    status_value = normalize_lookup_value(status_value)
    validate_datetime_range(reported_from, reported_to)

    query = select(Incident)
    if route_id is not None:
        query = query.where(Incident.route_id == route_id)
    if station_id is not None:
        query = query.where(Incident.station_id == station_id)
    if incident_type:
        query = query.where(func.lower(Incident.incident_type) == incident_type.lower())
    if severity:
        query = query.where(func.lower(Incident.severity) == severity.lower())
    if status_value:
        query = query.where(func.lower(Incident.status) == status_value.lower())
    if reported_from:
        query = query.where(Incident.reported_at >= reported_from)
    if reported_to:
        query = query.where(Incident.reported_at <= reported_to)
    query = query.order_by(Incident.reported_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: DBSession) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "incident not found")
    return incident


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: DBSession, _: AuthenticatedRole) -> Incident:
    validate_related_entities(db, payload.route_id, payload.station_id)

    incident = Incident(**payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: DBSession,
    _: OperatorRole,
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "incident not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(incident, field, value)

    validate_related_entities(db, incident.route_id, incident.station_id)

    db.commit()
    db.refresh(incident)
    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, db: DBSession, _: OperatorRole) -> Response:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "incident not found")

    db.delete(incident)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
