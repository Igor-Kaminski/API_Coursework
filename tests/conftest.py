from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db_session
from app.main import app
from app.db.base import Base
from app.models.incident import Incident
from app.models.journey_record import JourneyRecord
from app.models.route import Route
from app.models.station import Station


SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_reference_data(db_session: Session) -> dict[str, int]:
    leeds = Station(
        name="Leeds",
        code="LDS",
        crs_code="LDS",
        tiploc_code="LEEDS",
        city="Leeds",
        latitude=Decimal("53.794"),
        longitude=Decimal("-1.548"),
    )
    york = Station(
        name="York",
        code="YRK",
        crs_code="YRK",
        tiploc_code="YORK",
        city="York",
        latitude=Decimal("53.958"),
        longitude=Decimal("-1.093"),
    )
    db_session.add_all([leeds, york])
    db_session.flush()

    route = Route(
        origin_station_id=leeds.id,
        destination_station_id=york.id,
        name="Leeds to York",
        code="LDS-YRK",
        operator_name="LNER",
        distance_km=Decimal("40.20"),
        is_active=True,
    )
    db_session.add(route)
    db_session.commit()
    return {"leeds_id": leeds.id, "york_id": york.id, "route_id": route.id}


@pytest.fixture
def seeded_analytics_data(db_session: Session, seeded_reference_data: dict[str, int]) -> dict[str, int]:
    route_id = seeded_reference_data["route_id"]
    route = db_session.get(Route, route_id)
    assert route is not None

    records = [
        JourneyRecord(
            route_id=route_id,
            journey_date=date(2026, 3, 1),
            scheduled_departure=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            actual_departure=datetime(2026, 3, 1, 8, 0, tzinfo=UTC),
            scheduled_arrival=datetime(2026, 3, 1, 8, 45, tzinfo=UTC),
            actual_arrival=datetime(2026, 3, 1, 8, 45, tzinfo=UTC),
            delay_minutes=0,
            status="on_time",
            reason_for_delay=None,
            source="test",
            external_service_id="RID-1",
        ),
        JourneyRecord(
            route_id=route_id,
            journey_date=date(2026, 3, 2),
            scheduled_departure=datetime(2026, 3, 2, 9, 0, tzinfo=UTC),
            actual_departure=datetime(2026, 3, 2, 9, 10, tzinfo=UTC),
            scheduled_arrival=datetime(2026, 3, 2, 9, 45, tzinfo=UTC),
            actual_arrival=datetime(2026, 3, 2, 9, 55, tzinfo=UTC),
            delay_minutes=10,
            status="delayed",
            reason_for_delay="Signal failure",
            source="test",
            external_service_id="RID-2",
        ),
        JourneyRecord(
            route_id=route_id,
            journey_date=date(2026, 3, 3),
            scheduled_departure=datetime(2026, 3, 3, 10, 0, tzinfo=UTC),
            actual_departure=None,
            scheduled_arrival=datetime(2026, 3, 3, 10, 45, tzinfo=UTC),
            actual_arrival=None,
            delay_minutes=None,
            status="cancelled",
            reason_for_delay="Signal failure",
            source="test",
            external_service_id="RID-3",
        ),
    ]
    db_session.add_all(records)

    incidents = [
        Incident(
            route_id=route_id,
            station_id=seeded_reference_data["leeds_id"],
            title="Signal issue",
            description="Signal issue near Leeds",
            incident_type="infrastructure",
            severity="high",
            status="open",
            reported_at=datetime(2026, 3, 1, 7, 30, tzinfo=UTC),
        ),
        Incident(
            route_id=route_id,
            station_id=seeded_reference_data["york_id"],
            title="Weather delay",
            description="Weather disruption near York",
            incident_type="weather",
            severity="medium",
            status="investigating",
            reported_at=datetime(2026, 3, 1, 12, 0, tzinfo=UTC) + timedelta(days=1),
        ),
    ]
    db_session.add_all(incidents)
    db_session.commit()
    return seeded_reference_data
