import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.database import SessionLocal
from app.services.darwin_snapshot_service import DarwinSnapshotService
from app.services.journey_import_service import JourneyImportService
from app.services.route_import_service import RouteImportService
from app.services.station_import_service import StationImportService


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"missing required environment variable: {name}")
    return value


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Fetch and import a Darwin snapshot into the local database."
    )
    parser.add_argument(
        "--snapshot-path",
        help="Use an existing Darwin snapshot file instead of downloading a new one.",
    )
    parser.add_argument(
        "--download-dir",
        default="downloads",
        help="Directory for downloaded Darwin snapshots.",
    )
    parser.add_argument(
        "--max-services",
        type=int,
        default=None,
        help="Optional cap on the number of TS services to import.",
    )
    args = parser.parse_args()

    darwin_service = DarwinSnapshotService()
    if args.snapshot_path:
        snapshot_path = Path(args.snapshot_path)
    else:
        snapshot_path = darwin_service.fetch_latest_snapshot(
            host=require_env("DARWIN_FTP_HOST"),
            username=require_env("DARWIN_FTP_USER"),
            password=require_env("DARWIN_FTP_PASSWORD"),
            remote_directory=os.getenv("DARWIN_FTP_DIR", "snapshot"),
            download_directory=args.download_dir,
        )

    bundle = darwin_service.build_import_bundle(
        snapshot_path,
        max_services=args.max_services,
    )

    station_service = StationImportService()
    route_service = RouteImportService()
    journey_service = JourneyImportService()

    with SessionLocal() as session:
        station_result = station_service.import_records(session, bundle.station_records)
        route_result = route_service.import_records(session, bundle.route_records)
        journey_result = journey_service.import_records(session, bundle.journey_records)

    print(f"snapshot source: {snapshot_path}")
    print(
        f"stations imported: created={station_result.created} "
        f"updated={station_result.updated} skipped={station_result.skipped}"
    )
    print(
        f"routes imported: created={route_result.created} "
        f"updated={route_result.updated} skipped={route_result.skipped}"
    )
    print(
        f"journeys imported: created={journey_result.created} "
        f"updated={journey_result.updated} skipped={journey_result.skipped}"
    )


if __name__ == "__main__":
    main()
