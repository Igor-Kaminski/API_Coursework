import csv
import json
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.route import Route
from app.models.station import Station
from app.services.import_types import ImportResult, StationImportRecord


class StationImportService:
    """Imports station reference data into the local relational model."""

    def import_records(
        self,
        db: Session,
        records: Iterable[StationImportRecord],
    ) -> ImportResult:
        result = ImportResult()

        for record in records:
            station = self._find_existing_station(db, record)
            if station is None:
                station = Station(
                    name=record.name,
                    code=record.code,
                    tiploc_code=record.tiploc_code,
                    crs_code=record.crs_code,
                    city=record.city,
                    latitude=record.latitude,
                    longitude=record.longitude,
                )
                db.add(station)
                db.flush()
                result.created += 1
                continue

            changed = False
            for field in (
                "name",
                "code",
                "tiploc_code",
                "crs_code",
                "city",
                "latitude",
                "longitude",
            ):
                value = getattr(record, field)
                if field in {"code", "crs_code"} and value is not None:
                    self._merge_conflicting_station(db, station, value)
                if value is not None and getattr(station, field) != value:
                    setattr(station, field, value)
                    changed = True

            if changed:
                result.updated += 1
            else:
                result.skipped += 1

        db.commit()
        return result

    def load_records(self, source_path: str | Path) -> list[StationImportRecord]:
        path = Path(source_path)
        if path.suffix.lower() == ".csv":
            return self._load_csv(path)
        if path.suffix.lower() == ".json":
            return self._load_json(path)
        raise ValueError(f"unsupported station source format: {path.suffix}")

    def _find_existing_station(
        self,
        db: Session,
        record: StationImportRecord,
    ) -> Station | None:
        if record.tiploc_code:
            station = db.scalar(select(Station).where(Station.tiploc_code == record.tiploc_code))
            if station is not None:
                return station

            station = db.scalar(select(Station).where(Station.code == record.tiploc_code))
            if station is not None:
                return station

        if record.crs_code:
            station = db.scalar(select(Station).where(Station.crs_code == record.crs_code))
            if station is not None:
                return station

        if record.code:
            return db.scalar(select(Station).where(Station.code == record.code))

        return db.scalar(
            select(Station).where(func.lower(Station.name) == record.name.lower())
        )

    def _merge_conflicting_station(self, db: Session, target_station: Station, code_value: str) -> None:
        conflict = db.scalar(
            select(Station).where(
                Station.id != target_station.id,
                func.lower(Station.code) == code_value.lower(),
            )
        )
        if conflict is None:
            return

        for route in db.scalars(select(Route).where(Route.origin_station_id == conflict.id)):
            route.origin_station_id = target_station.id
        for route in db.scalars(select(Route).where(Route.destination_station_id == conflict.id)):
            route.destination_station_id = target_station.id
        for incident in db.scalars(select(Incident).where(Incident.station_id == conflict.id)):
            incident.station_id = target_station.id

        db.delete(conflict)
        db.flush()

    def _load_csv(self, path: Path) -> list[StationImportRecord]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [self._record_from_mapping(row) for row in reader]

    def _load_json(self, path: Path) -> list[StationImportRecord]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, dict):
            items = payload.get("stations") or payload.get("data") or []
        else:
            items = payload

        return [self._record_from_mapping(item) for item in items]

    def _record_from_mapping(self, payload: dict[str, object]) -> StationImportRecord:
        return StationImportRecord(
            name=self._pick_string(payload, "name", "station_name", "stationName"),
            code=self._pick_optional_string(payload, "code", "crs", "station_code"),
            tiploc_code=self._pick_optional_string(payload, "tiploc_code", "tiploc", "tpl"),
            crs_code=self._pick_optional_string(payload, "crs_code", "crs", "code"),
            city=self._pick_optional_string(payload, "city", "locality"),
            latitude=self._pick_decimal(payload, "latitude", "lat"),
            longitude=self._pick_decimal(payload, "longitude", "lon", "lng"),
        )

    def _pick_string(self, payload: dict[str, object], *keys: str) -> str:
        value = self._pick_optional_string(payload, *keys)
        if value is None:
            raise ValueError(f"missing required station field from keys: {keys}")
        return value

    def _pick_optional_string(
        self,
        payload: dict[str, object],
        *keys: str,
    ) -> str | None:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _pick_decimal(
        self,
        payload: dict[str, object],
        *keys: str,
    ) -> Decimal | None:
        value = self._pick_optional_string(payload, *keys)
        if value is None:
            return None
        return Decimal(value)
