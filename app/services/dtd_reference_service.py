from __future__ import annotations

import zipfile
from io import BytesIO
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

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
        station_result = StationImportService().import_records(db, records)
        renamed_routes = RouteNamingService().refresh_route_names(db)
        return station_result, renamed_routes

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
