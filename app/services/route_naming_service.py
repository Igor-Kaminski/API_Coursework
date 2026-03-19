from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.incident import Incident
from app.models.journey_record import JourneyRecord
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
        seen: dict[tuple[int, int, str], Route] = {}

        for route in routes:
            desired_name = f"{route.origin_station.name} to {route.destination_station.name}"
            key = (route.origin_station_id, route.destination_station_id, desired_name)
            canonical = seen.get(key)
            if canonical is None:
                seen[key] = route
                if route.name != desired_name:
                    route.name = desired_name
                    updated += 1
                continue

            self._merge_route_into(db, route, canonical)
            updated += 1

        db.commit()
        return updated

    def _merge_route_into(self, db: Session, source: Route, target: Route) -> None:
        for journey in db.scalars(select(JourneyRecord).where(JourneyRecord.route_id == source.id)):
            journey.route_id = target.id
        for incident in db.scalars(select(Incident).where(Incident.route_id == source.id)):
            incident.route_id = target.id
        db.flush()
        db.delete(source)
        db.flush()
