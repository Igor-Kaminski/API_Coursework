from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db_session
from app.models.route import Route
from app.schemas.route import RouteRead

router = APIRouter(prefix="/routes", tags=["routes"])
DBSession = Annotated[Session, Depends(get_db_session)]


@router.get("", response_model=list[RouteRead])
def list_routes(
    db: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Route]:
    query = (
        select(Route)
        .options(
            joinedload(Route.origin_station),
            joinedload(Route.destination_station),
        )
        .order_by(Route.name)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query))


@router.get("/{route_id}", response_model=RouteRead)
def get_route(route_id: int, db: DBSession) -> Route:
    query = (
        select(Route)
        .options(
            joinedload(Route.origin_station),
            joinedload(Route.destination_station),
        )
        .where(Route.id == route_id)
    )
    route = db.scalar(query)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="route not found",
        )
    return route
