from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import api_error, normalize_lookup_value, openapi_error_responses, validate_limit
from app.models.route import Route
from app.schemas.analytics import (
    DelayPatternPointRead,
    DelayReasonFrequencyRead,
    IncidentBreakdownPointRead,
    IncidentFrequencyPointRead,
    RouteCancellationRateRead,
    RouteDelayDistributionRead,
    RouteNameCoverageRead,
    RouteAverageDelayRead,
    RouteReliabilityRead,
    StationHotspotRead,
    TopCancelledRouteRead,
    TopDelayedRouteRead,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
DBSession = Annotated[Session, Depends(get_db_session)]
analytics_service = AnalyticsService()


def _require_route(db: Session, route_id: int) -> None:
    if db.get(Route, route_id) is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")


def _get_route_by_code(db: Session, route_code: str) -> Route:
    route_code = normalize_lookup_value(route_code)
    if route_code is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")

    route = db.scalar(select(Route).where(Route.code.ilike(route_code)))
    if route is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "route not found")
    return route


@router.get("/routes/{route_id}/reliability", response_model=RouteReliabilityRead, responses=openapi_error_responses(404))
def get_route_reliability(route_id: int, db: DBSession) -> RouteReliabilityRead:
    _require_route(db, route_id)
    return analytics_service.get_route_reliability(db, route_id)


@router.get("/routes/{route_id}/average-delay", response_model=RouteAverageDelayRead, responses=openapi_error_responses(404))
def get_route_average_delay(route_id: int, db: DBSession) -> RouteAverageDelayRead:
    _require_route(db, route_id)
    return analytics_service.get_route_average_delay(db, route_id)


@router.get("/routes/by-code/{route_code}/reliability", response_model=RouteReliabilityRead, responses=openapi_error_responses(404))
def get_route_reliability_by_code(route_code: str, db: DBSession) -> RouteReliabilityRead:
    route = _get_route_by_code(db, route_code)
    return analytics_service.get_route_reliability(db, route.id)


@router.get("/routes/by-code/{route_code}/average-delay", response_model=RouteAverageDelayRead, responses=openapi_error_responses(404))
def get_route_average_delay_by_code(route_code: str, db: DBSession) -> RouteAverageDelayRead:
    route = _get_route_by_code(db, route_code)
    return analytics_service.get_route_average_delay(db, route.id)


@router.get(
    "/routes/{route_id}/cancellation-rate",
    response_model=RouteCancellationRateRead,
    responses=openapi_error_responses(404),
)
def get_route_cancellation_rate(route_id: int, db: DBSession) -> RouteCancellationRateRead:
    _require_route(db, route_id)
    return analytics_service.get_route_cancellation_rate(db, route_id)


@router.get(
    "/routes/by-code/{route_code}/cancellation-rate",
    response_model=RouteCancellationRateRead,
    responses=openapi_error_responses(404),
)
def get_route_cancellation_rate_by_code(
    route_code: str,
    db: DBSession,
) -> RouteCancellationRateRead:
    route = _get_route_by_code(db, route_code)
    return analytics_service.get_route_cancellation_rate(db, route.id)


@router.get(
    "/routes/{route_id}/delay-distribution",
    response_model=RouteDelayDistributionRead,
    responses=openapi_error_responses(404),
)
def get_route_delay_distribution(route_id: int, db: DBSession) -> RouteDelayDistributionRead:
    _require_route(db, route_id)
    return analytics_service.get_route_delay_distribution(db, route_id)


@router.get(
    "/routes/by-code/{route_code}/delay-distribution",
    response_model=RouteDelayDistributionRead,
    responses=openapi_error_responses(404),
)
def get_route_delay_distribution_by_code(
    route_code: str,
    db: DBSession,
) -> RouteDelayDistributionRead:
    route = _get_route_by_code(db, route_code)
    return analytics_service.get_route_delay_distribution(db, route.id)


@router.get("/delay-patterns/hourly", response_model=list[DelayPatternPointRead])
def get_hourly_delay_patterns(db: DBSession) -> list[DelayPatternPointRead]:
    return analytics_service.get_hourly_delay_patterns(db)


@router.get("/stations/hotspots", response_model=list[StationHotspotRead])
def get_station_hotspots(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[StationHotspotRead]:
    validate_limit(limit)
    return analytics_service.get_station_hotspots(db, limit=limit)


@router.get("/incidents/frequency", response_model=list[IncidentFrequencyPointRead])
def get_incident_frequency(db: DBSession) -> list[IncidentFrequencyPointRead]:
    return analytics_service.get_incident_frequency(db)


@router.get(
    "/incidents/severity-breakdown",
    response_model=list[IncidentBreakdownPointRead],
)
def get_incident_severity_breakdown(db: DBSession) -> list[IncidentBreakdownPointRead]:
    return analytics_service.get_incident_severity_breakdown(db)


@router.get(
    "/incidents/status-breakdown",
    response_model=list[IncidentBreakdownPointRead],
)
def get_incident_status_breakdown(db: DBSession) -> list[IncidentBreakdownPointRead]:
    return analytics_service.get_incident_status_breakdown(db)


@router.get("/delay-reasons/common", response_model=list[DelayReasonFrequencyRead])
def get_common_delay_reasons(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[DelayReasonFrequencyRead]:
    validate_limit(limit)
    return analytics_service.get_common_delay_reasons(db, limit=limit)


@router.get(
    "/routes/top-delayed",
    response_model=list[TopDelayedRouteRead],
)
def get_top_delayed_routes(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=100),
    min_journeys: int = Query(default=1, ge=1, le=1000),
) -> list[TopDelayedRouteRead]:
    validate_limit(limit)
    return analytics_service.get_top_delayed_routes(db, limit=limit, min_journeys=min_journeys)


@router.get(
    "/routes/top-cancelled",
    response_model=list[TopCancelledRouteRead],
)
def get_top_cancelled_routes(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=100),
    min_journeys: int = Query(default=1, ge=1, le=1000),
) -> list[TopCancelledRouteRead]:
    validate_limit(limit)
    return analytics_service.get_top_cancelled_routes(
        db,
        limit=limit,
        min_journeys=min_journeys,
    )


@router.get(
    "/reference-data/route-name-coverage",
    response_model=RouteNameCoverageRead,
)
def get_route_name_coverage(
    db: DBSession,
    limit: int = Query(default=10, ge=1, le=100),
) -> RouteNameCoverageRead:
    validate_limit(limit)
    return analytics_service.get_route_name_coverage(db, limit=limit)
