from datetime import UTC, datetime, timedelta

from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models import Incident, Route, Station
from app.models.enums import IncidentType, Severity


TYPE_WEIGHTS = {
    IncidentType.delay: 2.0,
    IncidentType.cancellation: 8.0,
    IncidentType.signalling_issue: 6.0,
    IncidentType.weather: 5.0,
    IncidentType.staff_shortage: 4.0,
    IncidentType.congestion: 3.0,
    IncidentType.vehicle_fault: 6.0,
    IncidentType.other: 2.0,
}

SEVERITY_WEIGHTS = {
    Severity.low: 1.0,
    Severity.medium: 3.0,
    Severity.high: 6.0,
    Severity.critical: 10.0,
}


def resolve_window(from_date: datetime | None, to_date: datetime | None) -> tuple[datetime, datetime]:
    end = to_date or datetime.now(tz=UTC)
    start = from_date or (end - timedelta(days=30))
    if start > end:
        raise BadRequestError("'from' must be less than or equal to 'to'.")
    return start, end


def route_overview(db: Session, route_id: int, from_date: datetime | None, to_date: datetime | None) -> dict:
    start, end = resolve_window(from_date, to_date)
    route = db.get(Route, route_id)
    if route is None:
        raise NotFoundError(f"Route {route_id} was not found.")

    incidents = db.scalars(
        select(Incident).where(
            Incident.route_id == route_id,
            Incident.occurred_at >= start,
            Incident.occurred_at <= end,
        )
    ).all()

    incident_count = len(incidents)
    average_delay = (
        sum((incident.delay_minutes or 0) for incident in incidents if incident.delay_minutes is not None)
        / max(1, len([incident for incident in incidents if incident.delay_minutes is not None]))
        if any(incident.delay_minutes is not None for incident in incidents)
        else 0.0
    )
    cancellation_count = sum(1 for incident in incidents if incident.incident_type == IncidentType.cancellation)
    severe_incident_count = sum(
        1 for incident in incidents if incident.severity in {Severity.high, Severity.critical}
    )

    window_days = max((end - start).days, 1)
    total_penalty = 0.0
    for incident in incidents:
        delay_penalty = min(float(incident.delay_minutes or 0), 120.0) / 10.0
        total_penalty += TYPE_WEIGHTS[incident.incident_type] + SEVERITY_WEIGHTS[incident.severity] + delay_penalty
    reliability_score = max(0.0, min(100.0, 100.0 - (total_penalty / window_days)))

    return {
        "route_id": route_id,
        "from_date": start,
        "to_date": end,
        "incident_count": incident_count,
        "average_delay_minutes": round(average_delay, 2),
        "cancellation_count": cancellation_count,
        "severe_incident_count": severe_incident_count,
        "reliability_score": round(reliability_score, 2),
    }


def route_worst_time(db: Session, route_id: int, from_date: datetime | None, to_date: datetime | None) -> dict:
    start, end = resolve_window(from_date, to_date)
    route = db.get(Route, route_id)
    if route is None:
        raise NotFoundError(f"Route {route_id} was not found.")

    stmt = (
        select(
            extract("hour", Incident.occurred_at).label("hour"),
            func.count(Incident.id).label("incident_count"),
            func.coalesce(func.avg(Incident.delay_minutes), 0).label("average_delay_minutes"),
            func.sum(case((Incident.incident_type == IncidentType.cancellation, 1), else_=0)).label(
                "cancellation_count"
            ),
        )
        .where(
            Incident.route_id == route_id,
            Incident.occurred_at >= start,
            Incident.occurred_at <= end,
        )
        .group_by("hour")
    )
    rows = db.execute(stmt).all()
    if not rows:
        return {
            "route_id": route_id,
            "from_date": start,
            "to_date": end,
            "worst_hour": None,
            "incident_count": 0,
            "average_delay_minutes": 0.0,
            "cancellation_count": 0,
            "disruption_score": 0.0,
        }

    ranked_rows = []
    for row in rows:
        score = float(row.incident_count) + (float(row.average_delay_minutes) / 10.0) + (float(row.cancellation_count) * 2)
        ranked_rows.append((score, row))
    worst_score, worst_row = max(ranked_rows, key=lambda item: item[0])

    return {
        "route_id": route_id,
        "from_date": start,
        "to_date": end,
        "worst_hour": int(worst_row.hour),
        "incident_count": int(worst_row.incident_count),
        "average_delay_minutes": round(float(worst_row.average_delay_minutes), 2),
        "cancellation_count": int(worst_row.cancellation_count),
        "disruption_score": round(worst_score, 2),
    }


def top_delayed_stations(
    db: Session,
    *,
    limit: int,
    from_date: datetime | None,
    to_date: datetime | None,
) -> list[dict]:
    start, end = resolve_window(from_date, to_date)
    stmt = (
        select(
            Station.id.label("station_id"),
            Station.name.label("station_name"),
            Station.city.label("city"),
            func.count(Incident.id).label("incident_count"),
            func.coalesce(func.sum(Incident.delay_minutes), 0).label("total_delay_minutes"),
            func.coalesce(func.avg(Incident.delay_minutes), 0).label("average_delay_minutes"),
        )
        .join(Incident, Incident.station_id == Station.id)
        .where(Incident.occurred_at >= start, Incident.occurred_at <= end)
        .group_by(Station.id, Station.name, Station.city)
        .order_by(func.coalesce(func.sum(Incident.delay_minutes), 0).desc(), func.count(Incident.id).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "station_id": int(row.station_id),
            "station_name": row.station_name,
            "city": row.city,
            "incident_count": int(row.incident_count),
            "total_delay_minutes": int(row.total_delay_minutes),
            "average_delay_minutes": round(float(row.average_delay_minutes), 2),
        }
        for row in rows
    ]


def incidents_by_hour(db: Session, from_date: datetime | None, to_date: datetime | None) -> list[dict]:
    start, end = resolve_window(from_date, to_date)
    stmt = (
        select(
            extract("hour", Incident.occurred_at).label("hour"),
            func.count(Incident.id).label("incident_count"),
            func.coalesce(func.avg(Incident.delay_minutes), 0).label("average_delay_minutes"),
            func.sum(case((Incident.incident_type == IncidentType.cancellation, 1), else_=0)).label(
                "cancellation_count"
            ),
        )
        .where(Incident.occurred_at >= start, Incident.occurred_at <= end)
        .group_by("hour")
        .order_by("hour")
    )
    rows = db.execute(stmt).all()
    return [
        {
            "hour": int(row.hour),
            "incident_count": int(row.incident_count),
            "average_delay_minutes": round(float(row.average_delay_minutes), 2),
            "cancellation_count": int(row.cancellation_count),
        }
        for row in rows
    ]
