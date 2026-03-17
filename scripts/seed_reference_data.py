from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Incident, Route, Station
from app.models.enums import IncidentStatus, IncidentType, Severity, TransportMode


def seed_data() -> None:
    with SessionLocal() as session:
        if session.scalar(select(Station.id).limit(1)) is not None:
            print("Seed skipped: stations already exist.")
            return

        stations = [
            Station(name="Leeds", city="Leeds", code="LDS"),
            Station(name="York", city="York", code="YRK"),
            Station(name="Manchester Piccadilly", city="Manchester", code="MAN"),
            Station(name="Huddersfield", city="Huddersfield", code="HUD"),
        ]
        session.add_all(stations)
        session.flush()

        routes = [
            Route(
                name="Northern Express",
                origin_station_id=stations[0].id,
                destination_station_id=stations[1].id,
                transport_mode=TransportMode.train,
                active=True,
            ),
            Route(
                name="Pennine Connector",
                origin_station_id=stations[0].id,
                destination_station_id=stations[2].id,
                transport_mode=TransportMode.train,
                active=True,
            ),
            Route(
                name="West Yorkshire Shuttle",
                origin_station_id=stations[0].id,
                destination_station_id=stations[3].id,
                transport_mode=TransportMode.bus,
                active=True,
            ),
        ]
        session.add_all(routes)
        session.flush()

        incidents = [
            Incident(
                route_id=routes[0].id,
                station_id=stations[0].id,
                incident_type=IncidentType.delay,
                severity=Severity.medium,
                status=IncidentStatus.open,
                title="Platform congestion",
                description="Passenger crowding delayed dispatch by 12 minutes.",
                delay_minutes=12,
                occurred_at=datetime(2026, 3, 10, 7, 45, tzinfo=UTC),
            ),
            Incident(
                route_id=routes[0].id,
                station_id=stations[1].id,
                incident_type=IncidentType.cancellation,
                severity=Severity.high,
                status=IncidentStatus.resolved,
                title="Rolling stock fault",
                description="A technical fault caused one peak-time service to be cancelled.",
                delay_minutes=None,
                occurred_at=datetime(2026, 3, 10, 8, 15, tzinfo=UTC),
                resolved_at=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
            ),
            Incident(
                route_id=routes[1].id,
                station_id=stations[2].id,
                incident_type=IncidentType.staff_shortage,
                severity=Severity.medium,
                status=IncidentStatus.monitoring,
                title="Crew displacement",
                description="Replacement crew arrived late after an earlier disruption.",
                delay_minutes=25,
                occurred_at=datetime(2026, 3, 10, 9, 5, tzinfo=UTC),
            ),
            Incident(
                route_id=routes[2].id,
                station_id=stations[3].id,
                incident_type=IncidentType.weather,
                severity=Severity.low,
                status=IncidentStatus.resolved,
                title="Heavy rain disruption",
                description="Surface water increased journey times on the corridor.",
                delay_minutes=8,
                occurred_at=datetime(2026, 3, 10, 17, 20, tzinfo=UTC),
                resolved_at=datetime(2026, 3, 10, 18, 10, tzinfo=UTC),
            ),
        ]
        session.add_all(incidents)
        session.commit()

    print("Seed data inserted successfully.")


if __name__ == "__main__":
    seed_data()
