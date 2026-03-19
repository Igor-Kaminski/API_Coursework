import argparse

from app.core.database import SessionLocal
from app.services.journey_import_service import JourneyImportService


def main() -> None:
    parser = argparse.ArgumentParser(description="Import journey history data.")
    parser.add_argument("source", help="Path to a journey CSV, JSON, or XML file.")
    args = parser.parse_args()

    service = JourneyImportService()
    records = service.load_records(args.source)

    with SessionLocal() as session:
        result = service.import_records(session, records)

    print(
        f"journeys imported: created={result.created} "
        f"updated={result.updated} skipped={result.skipped}"
    )


if __name__ == "__main__":
    main()
