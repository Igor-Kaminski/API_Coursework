from math import asin, cos, radians, sin, sqrt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.route import Route


class RouteDistanceService:
    """Backfills approximate route distances from station coordinates."""

    def backfill_distances(self, db: Session) -> int:
        updated = 0
        routes = db.scalars(
            select(Route).options(
                joinedload(Route.origin_station),
                joinedload(Route.destination_station),
            )
        )

        for route in routes:
            origin = route.origin_station
            destination = route.destination_station
            if origin.latitude is None or origin.longitude is None:
                continue
            if destination.latitude is None or destination.longitude is None:
                continue

            distance_km = self._haversine_km(
                float(origin.latitude),
                float(origin.longitude),
                float(destination.latitude),
                float(destination.longitude),
            )
            quantized = Decimal(f"{distance_km:.2f}")
            if route.distance_km != quantized:
                route.distance_km = quantized
                updated += 1

        db.commit()
        return updated

    def _haversine_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        radius_km = 6371.0
        d_lat = radians(lat2 - lat1)
        d_lon = radians(lon2 - lon1)
        a = (
            sin(d_lat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
        )
        c = 2 * asin(sqrt(a))
        return radius_km * c
