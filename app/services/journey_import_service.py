import csv
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journey_record import JourneyRecord
from app.models.route import Route
from app.models.station import Station
from app.services.import_types import ImportResult, JourneyImportRecord


class JourneyImportService:
    """Imports normalized operational history records into journey_records."""

    def import_records(
        self,
        db: Session,
        records: Iterable[JourneyImportRecord],
    ) -> ImportResult:
        result = ImportResult()

        for record in records:
            route = self._resolve_route(db, record)
            existing = self._find_existing_journey(db, route.id, record)

            delay_minutes = self._calculate_delay_minutes(record)
            status = self._normalize_status(record, delay_minutes)

            if existing is None:
                journey = JourneyRecord(
                    route_id=route.id,
                    journey_date=record.journey_date,
                    scheduled_departure=record.scheduled_departure,
                    actual_departure=record.actual_departure,
                    scheduled_arrival=record.scheduled_arrival,
                    actual_arrival=record.actual_arrival,
                    delay_minutes=delay_minutes,
                    status=status,
                    reason_for_delay=record.reason_for_delay,
                    source=record.source,
                    external_service_id=record.external_service_id,
                )
                db.add(journey)
                db.flush()
                result.created += 1
                continue

            changed = False
            updates = {
                "actual_departure": record.actual_departure,
                "actual_arrival": record.actual_arrival,
                "delay_minutes": delay_minutes,
                "status": status,
                "reason_for_delay": record.reason_for_delay,
                "source": record.source,
            }
            for field, value in updates.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True

            if changed:
                result.updated += 1
            else:
                result.skipped += 1

        db.commit()
        return result

    def load_records(self, source_path: str | Path) -> list[JourneyImportRecord]:
        path = Path(source_path)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return self._load_csv(path)
        if suffix == ".json":
            return self._load_json(path)
        if suffix == ".xml":
            return self._load_xml(path)
        raise ValueError(f"unsupported journey source format: {path.suffix}")

    def _resolve_route(self, db: Session, record: JourneyImportRecord) -> Route:
        if record.route_code:
            route = db.scalar(select(Route).where(Route.code == record.route_code))
            if route is not None:
                return route

        origin_station = self._get_station_by_code(db, record.origin_station_code)
        destination_station = self._get_station_by_code(db, record.destination_station_code)

        route = db.scalar(
            select(Route).where(
                Route.origin_station_id == origin_station.id,
                Route.destination_station_id == destination_station.id,
                Route.name == record.route_name,
            )
        )
        if route is not None:
            return route

        route = Route(
            origin_station_id=origin_station.id,
            destination_station_id=destination_station.id,
            name=record.route_name,
            code=record.route_code,
            operator_name=record.operator_name,
        )
        db.add(route)
        db.flush()
        return route

    def _find_existing_journey(
        self,
        db: Session,
        route_id: int,
        record: JourneyImportRecord,
    ) -> JourneyRecord | None:
        if record.external_service_id:
            journey = db.scalar(
                select(JourneyRecord).where(
                    JourneyRecord.external_service_id == record.external_service_id,
                    JourneyRecord.journey_date == record.journey_date,
                )
            )
            if journey is not None:
                return journey

        return db.scalar(
            select(JourneyRecord).where(
                JourneyRecord.route_id == route_id,
                JourneyRecord.journey_date == record.journey_date,
                JourneyRecord.scheduled_departure == record.scheduled_departure,
            )
        )

    def _normalize_status(
        self,
        record: JourneyImportRecord,
        delay_minutes: int | None,
    ) -> str:
        if record.actual_departure is None and record.actual_arrival is None:
            return "cancelled"
        if delay_minutes is not None and delay_minutes > 0:
            return "delayed"
        return "on_time"

    def _calculate_delay_minutes(self, record: JourneyImportRecord) -> int | None:
        if record.actual_arrival is not None:
            delta = record.actual_arrival - record.scheduled_arrival
            return max(int(delta.total_seconds() // 60), 0)

        if record.actual_departure is not None:
            delta = record.actual_departure - record.scheduled_departure
            return max(int(delta.total_seconds() // 60), 0)

        return None

    def _get_station_by_code(self, db: Session, station_code: str) -> Station:
        station = db.scalar(select(Station).where(Station.code == station_code))
        if station is None:
            raise ValueError(f"station with code '{station_code}' was not found")
        return station

    def _load_csv(self, path: Path) -> list[JourneyImportRecord]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [self._record_from_mapping(row) for row in reader]

    def _load_json(self, path: Path) -> list[JourneyImportRecord]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, dict):
            items = payload.get("journeys") or payload.get("services") or payload.get("data") or []
        else:
            items = payload

        return [self._record_from_mapping(item) for item in items]

    def _load_xml(self, path: Path) -> list[JourneyImportRecord]:
        tree = ElementTree.parse(path)
        root = tree.getroot()

        records: list[JourneyImportRecord] = []
        for item in root.findall(".//service"):
            payload = {child.tag: (child.text or "").strip() for child in item}
            records.append(self._record_from_mapping(payload))
        return records

    def _record_from_mapping(self, payload: dict[str, object]) -> JourneyImportRecord:
        return JourneyImportRecord(
            route_code=self._pick_optional_string(payload, "route_code", "code"),
            origin_station_code=self._pick_string(payload, "origin_station_code", "origin_code", "origin"),
            destination_station_code=self._pick_string(
                payload,
                "destination_station_code",
                "destination_code",
                "destination",
            ),
            route_name=self._pick_string(payload, "route_name", "name"),
            operator_name=self._pick_optional_string(payload, "operator_name", "operator"),
            journey_date=self._parse_datetime(self._pick_string(payload, "journey_date")).date(),
            scheduled_departure=self._parse_datetime(
                self._pick_string(payload, "scheduled_departure")
            ),
            actual_departure=self._parse_optional_datetime(payload, "actual_departure"),
            scheduled_arrival=self._parse_datetime(self._pick_string(payload, "scheduled_arrival")),
            actual_arrival=self._parse_optional_datetime(payload, "actual_arrival"),
            reason_for_delay=self._pick_optional_string(payload, "reason_for_delay", "delay_reason"),
            source=self._pick_optional_string(payload, "source"),
            external_service_id=self._pick_optional_string(
                payload,
                "external_service_id",
                "service_id",
                "rid",
            ),
        )

    def _pick_string(self, payload: dict[str, object], *keys: str) -> str:
        value = self._pick_optional_string(payload, *keys)
        if value is None:
            raise ValueError(f"missing required journey field from keys: {keys}")
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

    def _parse_datetime(self, value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _parse_optional_datetime(
        self,
        payload: dict[str, object],
        *keys: str,
    ) -> datetime | None:
        value = self._pick_optional_string(payload, *keys)
        if value is None:
            return None
        return self._parse_datetime(value)
