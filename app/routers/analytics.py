from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.route import Route
from app.schemas.analytics import RouteReliabilityRead
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


@router.get("/routes/{route_id}/reliability", response_model=RouteReliabilityRead)
def get_route_reliability(route_id: int, db: DBSession) -> RouteReliabilityRead:
    _require_route(db, route_id)
    return analytics_service.get_route_reliability(db, route_id)
