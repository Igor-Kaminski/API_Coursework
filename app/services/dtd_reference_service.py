from __future__ import annotations

import zipfile
from io import BytesIO
from urllib.request import Request, urlopen

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.route import Route
from app.models.station import Station
from app.services.import_types import ImportResult, StationImportRecord
from app.services.route_naming_service import RouteNamingService
from app.services.station_import_service import StationImportService


class DTDReferenceService:
    """Loads TIPLOC to CRS/name mappings from the timetable MSN reference file."""

    def fetch_timetable_zip(self, url: str, auth_token: str) -> bytes:
        request = Request(url)
        request.add_header("X-Auth-Token", auth_token)
        with urlopen(request, timeout=180) as response:
            return response.read()

    def load_station_records_from_zip(self, payload: bytes) -> list[StationImportRecord]:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            msn_name = next(name for name in archive.namelist() if name.endswith(".MSN"))
            content = archive.read(msn_name).decode("utf-8", errors="ignore")
        return self._parse_msn_records(content)

    def enrich_database(
        self,
        db: Session,
        records: list[StationImportRecord],
    ) -> tuple[ImportResult, int]:
        self._backfill_legacy_tiploc_codes(db)
        existing_tiplocs = {
            value
            for value in db.scalars(select(Station.tiploc_code).where(Station.tiploc_code.is_not(None)))
            if value
        }
        crs_to_tiplocs: dict[str, set[str]] = {}
        for record in records:
            if not record.crs_code or not record.tiploc_code:
                continue
            crs_to_tiplocs.setdefault(record.crs_code, set()).add(record.tiploc_code)

        eligible_crs_targets = {
            value
            for value in db.scalars(
                select(Station.crs_code).where(
                    Station.crs_code.is_not(None),
                    Station.tiploc_code.is_(None),
                )
            )
            if value
        }

        filtered_records = []
        for record in records:
            if record.tiploc_code and record.tiploc_code in existing_tiplocs:
                filtered_records.append(record)
                continue

            if (
                record.crs_code
                and record.crs_code in eligible_crs_targets
                and len(crs_to_tiplocs.get(record.crs_code, set())) == 1
            ):
                filtered_records.append(record)
        self._collapse_alias_stations(db, filtered_records)
        filtered_records = self._deduplicate_records(filtered_records)

        station_result = StationImportService().import_records(db, filtered_records)
        renamed_routes = RouteNamingService().refresh_route_names(db)
        return station_result, renamed_routes

    def _backfill_legacy_tiploc_codes(self, db: Session) -> None:
        stations = db.scalars(
            select(Station).where(
                Station.tiploc_code.is_(None),
                Station.crs_code.is_(None),
                Station.code.is_not(None),
                func.length(Station.code) > 3,
            )
        )
        for station in stations:
            station.tiploc_code = station.code
        db.flush()

    def _deduplicate_records(self, records: list[StationImportRecord]) -> list[StationImportRecord]:
        deduped: dict[str, StationImportRecord] = {}
        for record in records:
            key = record.crs_code or record.code or record.tiploc_code or record.name
            deduped.setdefault(key, record)
        return list(deduped.values())

    def _collapse_alias_stations(self, db: Session, records: list[StationImportRecord]) -> None:
        grouped: dict[str, list[StationImportRecord]] = {}
        for record in records:
            if record.crs_code:
                grouped.setdefault(record.crs_code, []).append(record)

        for crs_code, group_records in grouped.items():
            tiplocs = [record.tiploc_code for record in group_records if record.tiploc_code]
            stations = list(
                db.scalars(
                    select(Station).where(
                        (Station.code == crs_code)
                        | (Station.crs_code == crs_code)
                        | (Station.tiploc_code.in_(tiplocs) if tiplocs else False)
                    )
                )
            )
            if len(stations) <= 1:
                continue

            canonical = next(
                (station for station in stations if station.code == crs_code or station.crs_code == crs_code),
                stations[0],
            )
            for station in stations:
                if station.id == canonical.id:
                    continue
                self._merge_station_into(db, station, canonical)
        db.flush()

    def _merge_station_into(self, db: Session, source: Station, target: Station) -> None:
        for route in db.scalars(select(Route).where(Route.origin_station_id == source.id)):
            route.origin_station_id = target.id
        for route in db.scalars(select(Route).where(Route.destination_station_id == source.id)):
            route.destination_station_id = target.id
        for incident in db.scalars(select(Incident).where(Incident.station_id == source.id)):
            incident.station_id = target.id

        source.code = None
        source.crs_code = None
        source.tiploc_code = None
        db.flush()
        db.delete(source)
        db.flush()

    def _parse_msn_records(self, content: str) -> list[StationImportRecord]:
        records: list[StationImportRecord] = []
        for line in content.splitlines():
            if not line.startswith("A"):
                continue

            name = line[5:35].strip()
            tiploc_code = line[36:43].strip()
            crs_code = line[43:46].strip() or None

            if not name or not tiploc_code:
                continue

            records.append(
                StationImportRecord(
                    name=name.title(),
                    code=crs_code,
                    tiploc_code=tiploc_code,
                    crs_code=crs_code,
                )
            )
        return records
