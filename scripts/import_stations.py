import argparse

from app.core.database import SessionLocal
from app.services.station_import_service import StationImportService


def main() -> None:
    parser = argparse.ArgumentParser(description="Import station reference data.")
    parser.add_argument("source", help="Path to a station CSV or JSON file.")
    args = parser.parse_args()

    service = StationImportService()
    records = service.load_records(args.source)

    with SessionLocal() as session:
        result = service.import_records(session, records)

    print(
        f"stations imported: created={result.created} "
        f"updated={result.updated} skipped={result.skipped}"
    )


if __name__ == "__main__":
    main()
