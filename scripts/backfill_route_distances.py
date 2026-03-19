from pathlib import Path

from dotenv import load_dotenv

from app.core.database import SessionLocal
from app.services.route_distance_service import RouteDistanceService


def main() -> None:
    load_dotenv(dotenv_path=Path(".env"))

    with SessionLocal() as session:
        updated = RouteDistanceService().backfill_distances(session)

    print(f"routes distance_km updated: {updated}")


if __name__ == "__main__":
    main()
