from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import DBSession
from app.schemas.analytics import HourlyIncidentSummary, RouteOverview, RouteWorstTime, StationDelaySummary
from app.services.analytics_service import incidents_by_hour, route_overview, route_worst_time, top_delayed_stations


router = APIRouter()


@router.get("/routes/{route_id}/overview", response_model=RouteOverview, summary="Route performance overview")
def get_route_overview(
    route_id: int,
    db: DBSession,
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
) -> dict:
    return route_overview(db, route_id, from_date, to_date)


@router.get("/routes/{route_id}/worst-time", response_model=RouteWorstTime, summary="Worst hour for a route")
def get_route_worst_time(
    route_id: int,
    db: DBSession,
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
) -> dict:
    return route_worst_time(db, route_id, from_date, to_date)


@router.get(
    "/stations/top-delayed",
    response_model=list[StationDelaySummary],
    summary="Most delay-affected stations",
)
def get_top_delayed_stations(
    db: DBSession,
    limit: int = Query(default=5, ge=1, le=20),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
) -> list[dict]:
    return top_delayed_stations(db, limit=limit, from_date=from_date, to_date=to_date)


@router.get("/incidents/by-hour", response_model=list[HourlyIncidentSummary], summary="Incident trends by hour")
def get_incidents_by_hour(
    db: DBSession,
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
) -> list[dict]:
    return incidents_by_hour(db, from_date, to_date)
