from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models import Incident, Route, Station
from app.models.enums import IncidentStatus


def get_station_or_404(db: Session, station_id: int) -> Station:
    station = db.get(Station, station_id)
    if station is None:
        raise NotFoundError(f"Station {station_id} was not found.")
    return station


def get_route_or_404(db: Session, route_id: int) -> Route:
    route = db.get(Route, route_id)
    if route is None:
        raise NotFoundError(f"Route {route_id} was not found.")
    return route


def get_incident_or_404(db: Session, incident_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise NotFoundError(f"Incident {incident_id} was not found.")
    return incident


def validate_station_and_route(db: Session, route_id: int, station_id: int | None) -> None:
    route = get_route_or_404(db, route_id)
    if station_id is None:
        return

    station = get_station_or_404(db, station_id)
    valid_station_ids = {route.origin_station_id, route.destination_station_id}
    if station.id not in valid_station_ids:
        raise BadRequestError("The station must match the route origin or destination.")


def apply_incident_filters(
    stmt: Select[tuple[Incident]],
    *,
    route_id: int | None = None,
    station_id: int | None = None,
    incident_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    min_delay: int | None = None,
) -> Select[tuple[Incident]]:
    if from_date and to_date and from_date > to_date:
        raise BadRequestError("'from' must be less than or equal to 'to'.")

    if route_id is not None:
        stmt = stmt.where(Incident.route_id == route_id)
    if station_id is not None:
        stmt = stmt.where(Incident.station_id == station_id)
    if incident_type is not None:
        stmt = stmt.where(Incident.incident_type == incident_type)
    if severity is not None:
        stmt = stmt.where(Incident.severity == severity)
    if status is not None:
        stmt = stmt.where(Incident.status == status)
    if from_date is not None:
        stmt = stmt.where(Incident.occurred_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Incident.occurred_at <= to_date)
    if min_delay is not None:
        stmt = stmt.where(Incident.delay_minutes.is_not(None), Incident.delay_minutes >= min_delay)

    return stmt


def list_incidents(
    db: Session,
    *,
    route_id: int | None,
    station_id: int | None,
    incident_type: str | None,
    severity: str | None,
    status: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
    min_delay: int | None,
    limit: int,
    offset: int,
) -> Iterable[Incident]:
    stmt = select(Incident).order_by(Incident.occurred_at.desc())
    stmt = apply_incident_filters(
        stmt,
        route_id=route_id,
        station_id=station_id,
        incident_type=incident_type,
        severity=severity,
        status=status,
        from_date=from_date,
        to_date=to_date,
        min_delay=min_delay,
    )
    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


def _strip_tz(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def apply_status_patch(incident: Incident, status: IncidentStatus, resolved_at: datetime | None) -> Incident:
    if status == IncidentStatus.resolved:
        if resolved_at is None:
            raise BadRequestError("resolved incidents must include resolved_at.")
        if _strip_tz(resolved_at) < _strip_tz(incident.occurred_at):
            raise BadRequestError("resolved_at must be greater than or equal to occurred_at.")
    else:
        resolved_at = None

    incident.status = status
    incident.resolved_at = resolved_at
    return incident
