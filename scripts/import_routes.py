import argparse

from app.core.database import SessionLocal
from app.services.route_import_service import RouteImportService


def main() -> None:
    parser = argparse.ArgumentParser(description="Import route reference data.")
    parser.add_argument("source", help="Path to a route CSV or JSON file.")
    args = parser.parse_args()

    service = RouteImportService()
    records = service.load_records(args.source)

    with SessionLocal() as session:
        result = service.import_records(session, records)

    print(
        f"routes imported: created={result.created} "
        f"updated={result.updated} skipped={result.skipped}"
    )


if __name__ == "__main__":
    main()
