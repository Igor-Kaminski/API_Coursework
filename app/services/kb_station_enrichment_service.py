from __future__ import annotations

import json
import zipfile
from base64 import b64encode
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from sqlalchemy.orm import Session

from app.services.import_types import ImportResult, StationImportRecord
from app.services.route_naming_service import RouteNamingService
from app.services.station_import_service import StationImportService


class KBStationEnrichmentService:
    """Loads station reference metadata from KB-style feeds and enriches stations."""

    def fetch_feed(
        self,
        url: str,
        *,
        auth_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> bytes:
        request = Request(url)
        if auth_token:
            request.add_header("X-Auth-Token", auth_token)
            request.add_header("Auth-Token", auth_token)
        elif username and password:
            request.add_header(
                "Authorization",
                "Basic " + b64encode(f"{username}:{password}".encode()).decode(),
            )

        with urlopen(request, timeout=120) as response:
            return response.read()

    def load_records_from_bytes(self, payload: bytes) -> list[StationImportRecord]:
        if payload.startswith(b"PK"):
            return self._load_records_from_zip(payload)
        if payload.lstrip().startswith(b"{") or payload.lstrip().startswith(b"["):
            return self._load_records_from_json(payload.decode("utf-8"))
        return self._load_records_from_xml(payload.decode("utf-8", errors="ignore"))

    def load_records_from_path(self, source_path: str | Path) -> list[StationImportRecord]:
        path = Path(source_path)
        if path.suffix.lower() == ".zip":
            return self._load_records_from_zip(path.read_bytes())
        if path.suffix.lower() == ".json":
            return self._load_records_from_json(path.read_text(encoding="utf-8"))
        return self._load_records_from_xml(path.read_text(encoding="utf-8", errors="ignore"))

    def enrich_database(
        self,
        db: Session,
        records: list[StationImportRecord],
    ) -> tuple[ImportResult, int]:
        station_result = StationImportService().import_records(db, records)
        renamed_routes = RouteNamingService().refresh_route_names(db)
        return station_result, renamed_routes

    def _load_records_from_zip(self, payload: bytes) -> list[StationImportRecord]:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            for name in archive.namelist():
                lowered = name.lower()
                if lowered.endswith(".xml"):
                    return self._load_records_from_xml(archive.read(name).decode("utf-8", errors="ignore"))
                if lowered.endswith(".json"):
                    return self._load_records_from_json(archive.read(name).decode("utf-8"))
        raise ValueError("no supported KB stations file found in zip archive")

    def _load_records_from_json(self, content: str) -> list[StationImportRecord]:
        payload = json.loads(content)
        if isinstance(payload, dict):
            items = payload.get("stations") or payload.get("data") or payload.get("Station") or []
        else:
            items = payload
        return [record for item in items if (record := self._record_from_mapping(item)) is not None]

    def _load_records_from_xml(self, content: str) -> list[StationImportRecord]:
        root = ElementTree.fromstring(content)
        records: list[StationImportRecord] = []
        for element in root.iter():
            local_name = self._local_name(element.tag).lower()
            if local_name not in {"station", "stationitem", "stationdetails"}:
                continue
            record = self._record_from_xml_element(element)
            if record is not None:
                records.append(record)
        return records

    def _record_from_xml_element(self, element) -> StationImportRecord | None:
        name = self._find_text(
            element,
            "name",
            "stationname",
            "station_name",
            "name16",
            "sixteencharactername",
        )
        tiploc_code = self._find_text(element, "tiploc", "tiploccode", "tiploc_code", "tpl")
        crs_code = self._find_text(element, "crs", "crscode", "crs_code", "threealphacode")
        city = self._find_text(element, "city", "locality", "localityname", "town")
        latitude = self._find_decimal(element, "latitude", "lat")
        longitude = self._find_decimal(element, "longitude", "lon", "lng")

        if not name or not (tiploc_code or crs_code):
            return None

        return StationImportRecord(
            name=name,
            code=crs_code,
            tiploc_code=tiploc_code,
            crs_code=crs_code,
            city=city,
            latitude=latitude,
            longitude=longitude,
        )

    def _record_from_mapping(self, payload: dict[str, object]) -> StationImportRecord | None:
        lower_map = {str(key).lower(): value for key, value in payload.items()}
        name = self._pick_mapping_value(
            lower_map,
            "name",
            "stationname",
            "station_name",
            "name16",
            "sixteencharactername",
        )
        tiploc_code = self._pick_mapping_value(lower_map, "tiploc", "tiploccode", "tiploc_code", "tpl")
        crs_code = self._pick_mapping_value(lower_map, "crs", "crscode", "crs_code", "threealphacode")
        city = self._pick_mapping_value(lower_map, "city", "locality", "localityname", "town")
        latitude = self._pick_mapping_decimal(lower_map, "latitude", "lat")
        longitude = self._pick_mapping_decimal(lower_map, "longitude", "lon", "lng")

        if not name or not (tiploc_code or crs_code):
            return None

        return StationImportRecord(
            name=name,
            code=crs_code,
            tiploc_code=tiploc_code,
            crs_code=crs_code,
            city=city,
            latitude=latitude,
            longitude=longitude,
        )

    def _find_text(self, element, *candidate_names: str) -> str | None:
        candidate_set = {name.lower() for name in candidate_names}
        for child in element.iter():
            local_name = self._local_name(child.tag).lower()
            if local_name not in candidate_set:
                continue
            text = (child.text or "").strip()
            if text:
                return text
        return None

    def _pick_mapping_value(self, payload: dict[str, object], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key.lower())
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _find_decimal(self, element, *candidate_names: str) -> Decimal | None:
        value = self._find_text(element, *candidate_names)
        if value is None:
            return None
        return Decimal(value)

    def _pick_mapping_decimal(self, payload: dict[str, object], *keys: str) -> Decimal | None:
        value = self._pick_mapping_value(payload, *keys)
        if value is None:
            return None
        return Decimal(value)

    def _local_name(self, tag: str) -> str:
        return tag.split("}", 1)[1] if "}" in tag else tag
