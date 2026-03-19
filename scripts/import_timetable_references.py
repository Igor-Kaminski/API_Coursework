import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.database import SessionLocal
from app.services.dtd_reference_service import DTDReferenceService


def main() -> None:
    load_dotenv(dotenv_path=Path(".env"))

    parser = argparse.ArgumentParser(
        description="Enrich stations from the timetable MSN reference file and refresh route names."
    )
    parser.add_argument(
        "--timetable-url",
        default="https://opendata.nationalrail.co.uk/api/staticfeeds/3.0/timetable",
        help="DTD timetable static feed URL.",
    )
    args = parser.parse_args()

    auth_token = os.environ["KB_AUTH_TOKEN"]
    service = DTDReferenceService()
    payload = service.fetch_timetable_zip(args.timetable_url, auth_token=auth_token)
    records = service.load_station_records_from_zip(payload)

    with SessionLocal() as session:
        station_result, renamed_routes = service.enrich_database(session, records)

    print(
        f"timetable references enriched: created={station_result.created} "
        f"updated={station_result.updated} skipped={station_result.skipped}"
    )
    print(f"routes renamed: {renamed_routes}")


if __name__ == "__main__":
    main()
