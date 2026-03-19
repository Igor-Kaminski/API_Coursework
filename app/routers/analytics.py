from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.route import Route
from app.schemas.analytics import (
    DelayPatternPointRead,
    DelayReasonFrequencyRead,
    IncidentFrequencyPointRead,
    RouteNameCoverageRead,
    RouteAverageDelayRead,
    RouteReliabilityRead,
    StationHotspotRead,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
DBSession = Annotated[Session, Depends(get_db_session)]
analytics_service = AnalyticsService()


def _require_route(db: Session, route_id: int) -> None:
    if db.get(Route, route_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="route not found",
        )


def _get_route_by_code(db: Session, route_code: str) -> Route:
    route = db.scalar(select(Route).where(Route.code == route_code))
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="route not found",
        )
    return route


@router.get("/routes/{route_id}/reliability", response_model=RouteReliabilityRead)
def get_route_reliability(route_id: int, db: DBSession) -> RouteReliabilityRead:
    _require_route(db, route_id)
    return analytics_service.get_route_reliability(db, route_id)


@router.get("/routes/{route_id}/average-delay", response_model=RouteAverageDelayRead)
def get_route_average_delay(route_id: int, db: DBSession) -> RouteAverageDelayRead:
    _require_route(db, route_id)
    return analytics_service.get_route_average_delay(db, route_id)


@router.get("/routes/by-code/{route_code}/reliability", response_model=RouteReliabilityRead)
def get_route_reliability_by_code(route_code: str, db: DBSession) -> RouteReliabilityRead:
    route = _get_route_by_code(db, route_code)
    return analytics_service.get_route_reliability(db, route.id)


@router.get("/routes/by-code/{route_code}/average-delay", response_model=RouteAverageDelayRead)
def get_route_average_delay_by_code(route_code: str, db: DBSession) -> RouteAverageDelayRead:
    route = _get_route_by_code(db, route_code)
    return analytics_service.get_route_average_delay(db, route.id)


@router.get("/delay-patterns/hourly", response_model=list[DelayPatternPointRead])
def get_hourly_delay_patterns(db: DBSession) -> list[DelayPatternPointRead]:
    return analytics_service.get_hourly_delay_patterns(db)


@router.get("/delay-patterns/daily", response_model=list[DelayPatternPointRead])
def get_daily_delay_patterns(db: DBSession) -> list[DelayPatternPointRead]:
    return analytics_service.get_daily_delay_patterns(db)


@router.get("/stations/hotspots", response_model=list[StationHotspotRead])
def get_station_hotspots(db: DBSession, limit: int = 10) -> list[StationHotspotRead]:
    return analytics_service.get_station_hotspots(db, limit=limit)


@router.get("/incidents/frequency", response_model=list[IncidentFrequencyPointRead])
def get_incident_frequency(db: DBSession) -> list[IncidentFrequencyPointRead]:
    return analytics_service.get_incident_frequency(db)


@router.get("/delay-reasons/common", response_model=list[DelayReasonFrequencyRead])
def get_common_delay_reasons(
    db: DBSession,
    limit: int = 10,
) -> list[DelayReasonFrequencyRead]:
    return analytics_service.get_common_delay_reasons(db, limit=limit)


@router.get(
    "/reference-data/route-name-coverage",
    response_model=RouteNameCoverageRead,
)
def get_route_name_coverage(
    db: DBSession,
    limit: int = 10,
) -> RouteNameCoverageRead:
    return analytics_service.get_route_name_coverage(db, limit=limit)
