import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.database import SessionLocal
from app.services.kb_station_enrichment_service import KBStationEnrichmentService


def main() -> None:
    load_dotenv(dotenv_path=Path(".env"))

    parser = argparse.ArgumentParser(
        description="Enrich stations from a KB feed and refresh route names."
    )
    parser.add_argument(
        "--source-path",
        help="Local KB stations XML/JSON/ZIP file. If omitted, fetch from KB_STATIONS_URL.",
    )
    args = parser.parse_args()

    service = KBStationEnrichmentService()
    if args.source_path:
        records = service.load_records_from_path(args.source_path)
    else:
        payload = service.fetch_feed(
            os.environ["KB_STATIONS_URL"],
            auth_token=os.getenv("KB_AUTH_TOKEN"),
            username=os.getenv("KB_USERNAME"),
            password=os.getenv("KB_PASSWORD"),
        )
        records = service.load_records_from_bytes(payload)

    with SessionLocal() as session:
        station_result, renamed_routes = service.enrich_database(session, records)

    print(
        f"stations enriched: created={station_result.created} "
        f"updated={station_result.updated} skipped={station_result.skipped}"
    )
    print(f"routes renamed: {renamed_routes}")


if __name__ == "__main__":
    main()
