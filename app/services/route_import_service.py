import csv
import json
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.route import Route
from app.models.station import Station
from app.services.import_types import ImportResult, RouteImportRecord


class RouteImportService:
    """Imports or derives route reference data using existing stations."""

    def import_records(
        self,
        db: Session,
        records: Iterable[RouteImportRecord],
    ) -> ImportResult:
        result = ImportResult()

        for record in records:
            origin_station = self._get_station_by_code(db, record.origin_station_code)
            destination_station = self._get_station_by_code(db, record.destination_station_code)

            route = db.scalar(
                select(Route).where(
                    Route.origin_station_id == origin_station.id,
                    Route.destination_station_id == destination_station.id,
                    Route.name == record.name,
                )
            )

            if route is None:
                route = Route(
                    origin_station_id=origin_station.id,
                    destination_station_id=destination_station.id,
                    name=record.name,
                    code=record.code,
                    operator_name=record.operator_name,
                    distance_km=record.distance_km,
                    is_active=record.is_active,
                )
                db.add(route)
                db.flush()
                result.created += 1
                continue

            changed = False
            for field in ("code", "operator_name", "distance_km", "is_active"):
                value = getattr(record, field)
                if value is not None and getattr(route, field) != value:
                    setattr(route, field, value)
                    changed = True

            if changed:
                result.updated += 1
            else:
                result.skipped += 1

        db.commit()
        return result

    def load_records(self, source_path: str | Path) -> list[RouteImportRecord]:
        path = Path(source_path)
        if path.suffix.lower() == ".csv":
            return self._load_csv(path)
        if path.suffix.lower() == ".json":
            return self._load_json(path)
        raise ValueError(f"unsupported route source format: {path.suffix}")

    def _get_station_by_code(self, db: Session, station_code: str) -> Station:
        station = db.scalar(
            select(Station).where(
                or_(
                    Station.code == station_code,
                    Station.tiploc_code == station_code,
                    Station.crs_code == station_code,
                )
            )
        )
        if station is None:
            raise ValueError(f"station with code '{station_code}' was not found")
        return station

    def _load_csv(self, path: Path) -> list[RouteImportRecord]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [self._record_from_mapping(row) for row in reader]

    def _load_json(self, path: Path) -> list[RouteImportRecord]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, dict):
            items = payload.get("routes") or payload.get("data") or []
        else:
            items = payload

        return [self._record_from_mapping(item) for item in items]

    def _record_from_mapping(self, payload: dict[str, object]) -> RouteImportRecord:
        return RouteImportRecord(
            origin_station_code=self._pick_string(
                payload,
                "origin_station_code",
                "origin_code",
                "origin",
            ),
            destination_station_code=self._pick_string(
                payload,
                "destination_station_code",
                "destination_code",
                "destination",
            ),
            name=self._pick_string(payload, "name", "route_name"),
            code=self._pick_optional_string(payload, "code", "route_code"),
            operator_name=self._pick_optional_string(payload, "operator_name", "operator"),
            distance_km=self._pick_decimal(payload, "distance_km"),
            is_active=self._pick_bool(payload, "is_active", default=True),
        )

    def _pick_string(self, payload: dict[str, object], *keys: str) -> str:
        value = self._pick_optional_string(payload, *keys)
        if value is None:
            raise ValueError(f"missing required route field from keys: {keys}")
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

    def _pick_bool(self, payload: dict[str, object], *keys: str, default: bool) -> bool:
        value = self._pick_optional_string(payload, *keys)
        if value is None:
            return default
        return value.lower() in {"1", "true", "yes", "y"}
