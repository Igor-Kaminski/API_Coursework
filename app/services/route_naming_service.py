from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.route import Route


class RouteNamingService:
    """Refreshes route names from linked station display names."""

    def refresh_route_names(self, db: Session) -> int:
        updated = 0
        routes = db.scalars(
            select(Route).options(
                joinedload(Route.origin_station),
                joinedload(Route.destination_station),
            )
        )

        for route in routes:
            desired_name = f"{route.origin_station.name} to {route.destination_station.name}"
            if route.name != desired_name:
                route.name = desired_name
                updated += 1

        db.commit()
        return updated
