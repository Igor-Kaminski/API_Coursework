from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.incident import Incident
from app.models.journey_record import JourneyRecord
from app.models.route import Route
from app.schemas.analytics import (
    DelayPatternPointRead,
    DelayReasonFrequencyRead,
    IncidentFrequencyPointRead,
    RouteNameCoverageRead,
    RouteAverageDelayRead,
    RouteReliabilityRead,
    StationHotspotRead,
    UnresolvedLocationRead,
)


class AnalyticsService:
    """Computes coursework-friendly analytics from stored local data."""

    def get_route_reliability(self, db: Session, route_id: int) -> RouteReliabilityRead:
        records = list(
            db.scalars(
                select(JourneyRecord).where(JourneyRecord.route_id == route_id)
            )
        )

        total = len(records)
        if total == 0:
            return RouteReliabilityRead(
                route_id=route_id,
                total_journeys=0,
                on_time_percentage=0.0,
                delayed_percentage=0.0,
                cancelled_percentage=0.0,
            )

        counts = defaultdict(int)
        for record in records:
            counts[record.status] += 1

        return RouteReliabilityRead(
            route_id=route_id,
            total_journeys=total,
            on_time_percentage=round(counts["on_time"] * 100 / total, 2),
            delayed_percentage=round(counts["delayed"] * 100 / total, 2),
            cancelled_percentage=round(counts["cancelled"] * 100 / total, 2),
        )

    def get_route_average_delay(self, db: Session, route_id: int) -> RouteAverageDelayRead:
        delays = [
            record.delay_minutes
            for record in db.scalars(
                select(JourneyRecord).where(JourneyRecord.route_id == route_id)
            )
            if record.delay_minutes is not None
        ]

        total = len(delays)
        average = round(sum(delays) / total, 2) if total else 0.0
        return RouteAverageDelayRead(
            route_id=route_id,
            total_journeys=total,
            average_delay_minutes=average,
        )

    def get_hourly_delay_patterns(self, db: Session) -> list[DelayPatternPointRead]:
        buckets: dict[int, list[int]] = defaultdict(list)
        for record in db.scalars(select(JourneyRecord)):
            if record.delay_minutes is None:
                continue
            buckets[record.scheduled_departure.hour].append(record.delay_minutes)

        return [
            DelayPatternPointRead(
                bucket=f"{hour:02d}:00",
                total_journeys=len(values),
                average_delay_minutes=round(sum(values) / len(values), 2),
            )
            for hour, values in sorted(buckets.items())
        ]

    def get_daily_delay_patterns(self, db: Session) -> list[DelayPatternPointRead]:
        buckets: dict[str, list[int]] = defaultdict(list)
        for record in db.scalars(select(JourneyRecord)):
            if record.delay_minutes is None:
                continue
            day_name = record.journey_date.strftime("%A")
            buckets[day_name].append(record.delay_minutes)

        ordered_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        return [
            DelayPatternPointRead(
                bucket=day_name,
                total_journeys=len(buckets[day_name]),
                average_delay_minutes=round(sum(buckets[day_name]) / len(buckets[day_name]), 2),
            )
            for day_name in ordered_days
            if day_name in buckets
        ]

    def get_station_hotspots(
        self,
        db: Session,
        limit: int = 10,
    ) -> list[StationHotspotRead]:
        buckets: dict[tuple[int, str], list[int]] = defaultdict(list)
        records = db.scalars(
            select(JourneyRecord)
            .options(
                joinedload(JourneyRecord.route).joinedload(Route.origin_station),
                joinedload(JourneyRecord.route).joinedload(Route.destination_station),
            )
            .where(JourneyRecord.delay_minutes.is_not(None))
        )

        for record in records:
            delay = record.delay_minutes or 0
            route = record.route
            for station in (route.origin_station, route.destination_station):
                buckets[(station.id, station.name)].append(delay)

        hotspots = [
            StationHotspotRead(
                station_id=station_id,
                station_name=station_name,
                affected_journeys=len(values),
                average_delay_minutes=round(sum(values) / len(values), 2),
            )
            for (station_id, station_name), values in buckets.items()
        ]
        hotspots.sort(key=lambda item: (-item.affected_journeys, -item.average_delay_minutes))
        return hotspots[:limit]

    def get_incident_frequency(self, db: Session) -> list[IncidentFrequencyPointRead]:
        buckets: dict[str, int] = defaultdict(int)
        for incident in db.scalars(select(Incident).order_by(Incident.reported_at)):
            bucket = incident.reported_at.date().isoformat()
            buckets[bucket] += 1

        return [
            IncidentFrequencyPointRead(bucket=bucket, total_incidents=total)
            for bucket, total in sorted(buckets.items())
        ]

    def get_common_delay_reasons(
        self,
        db: Session,
        limit: int = 10,
    ) -> list[DelayReasonFrequencyRead]:
        buckets: dict[str, int] = defaultdict(int)
        for record in db.scalars(select(JourneyRecord)):
            if not record.reason_for_delay:
                continue
            buckets[record.reason_for_delay.strip()] += 1

        reasons = [
            DelayReasonFrequencyRead(reason=reason, total_occurrences=total)
            for reason, total in buckets.items()
        ]
        reasons.sort(key=lambda item: (-item.total_occurrences, item.reason))
        return reasons[:limit]

    def get_route_name_coverage(
        self,
        db: Session,
        limit: int = 10,
    ) -> RouteNameCoverageRead:
        routes = list(
            db.scalars(
                select(Route).options(
                    joinedload(Route.origin_station),
                    joinedload(Route.destination_station),
                )
            )
        )

        fully_human_readable = 0
        partially_unresolved = 0
        fully_unresolved = 0
        unresolved_counts: dict[tuple[int, str], int] = defaultdict(int)

        for route in routes:
            origin_resolved = route.origin_station.crs_code is not None
            destination_resolved = route.destination_station.crs_code is not None

            if origin_resolved and destination_resolved:
                fully_human_readable += 1
                continue

            if origin_resolved or destination_resolved:
                partially_unresolved += 1
            else:
                fully_unresolved += 1

            if not origin_resolved:
                unresolved_counts[(route.origin_station.id, route.origin_station.name)] += 1
            if not destination_resolved:
                unresolved_counts[(route.destination_station.id, route.destination_station.name)] += 1

        top_unresolved_locations = [
            UnresolvedLocationRead(
                station_id=station_id,
                station_name=station_name,
                unresolved_route_count=count,
            )
            for (station_id, station_name), count in unresolved_counts.items()
        ]
        top_unresolved_locations.sort(
            key=lambda item: (-item.unresolved_route_count, item.station_name)
        )

        return RouteNameCoverageRead(
            total_routes=len(routes),
            fully_human_readable_routes=fully_human_readable,
            partially_unresolved_routes=partially_unresolved,
            fully_unresolved_routes=fully_unresolved,
            unresolved_location_count=len(unresolved_counts),
            top_unresolved_locations=top_unresolved_locations[:limit],
        )
