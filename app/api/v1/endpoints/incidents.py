from datetime import datetime

from fastapi import APIRouter, Query, Response, status

from app.api.deps import AdminUser, DBSession, OperatorOrAdmin
from app.models import Incident
from app.models.enums import IncidentStatus, IncidentType, Severity
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentStatusUpdate, IncidentUpdate
from app.services.incident_service import (
    apply_status_patch,
    get_incident_or_404,
    list_incidents,
    validate_station_and_route,
)


router = APIRouter()


@router.get("", response_model=list[IncidentRead], summary="List incidents")
def get_incidents(
    db: DBSession,
    route_id: int | None = Query(default=None, gt=0),
    station_id: int | None = Query(default=None, gt=0),
    incident_type: IncidentType | None = Query(default=None),
    severity: Severity | None = Query(default=None),
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    min_delay: int | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Incident]:
    return list(
        list_incidents(
            db,
            route_id=route_id,
            station_id=station_id,
            incident_type=incident_type,
            severity=severity,
            status=status_filter,
            from_date=from_date,
            to_date=to_date,
            min_delay=min_delay,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{incident_id}", response_model=IncidentRead, summary="Get incident")
def get_incident(incident_id: int, db: DBSession) -> Incident:
    return get_incident_or_404(db, incident_id)


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED, summary="Create incident")
def create_incident(payload: IncidentCreate, db: DBSession, _: OperatorOrAdmin) -> Incident:
    validate_station_and_route(db, payload.route_id, payload.station_id)
    incident = Incident(**payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.put("/{incident_id}", response_model=IncidentRead, summary="Update incident")
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: DBSession,
    _: OperatorOrAdmin,
) -> Incident:
    incident = get_incident_or_404(db, incident_id)
    validate_station_and_route(db, payload.route_id, payload.station_id)
    for field, value in payload.model_dump().items():
        setattr(incident, field, value)
    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/{incident_id}/status", response_model=IncidentRead, summary="Update incident status")
def update_incident_status(
    incident_id: int,
    payload: IncidentStatusUpdate,
    db: DBSession,
    _: OperatorOrAdmin,
) -> Incident:
    incident = get_incident_or_404(db, incident_id)
    apply_status_patch(incident, payload.status, payload.resolved_at)
    db.commit()
    db.refresh(incident)
    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete incident")
def delete_incident(incident_id: int, db: DBSession, _: AdminUser) -> Response:
    incident = get_incident_or_404(db, incident_id)
    db.delete(incident)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
