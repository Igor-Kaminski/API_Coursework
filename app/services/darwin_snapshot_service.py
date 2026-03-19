from __future__ import annotations

import gzip
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from ftplib import FTP
from pathlib import Path
from xml.etree import ElementTree

from app.services.import_types import JourneyImportRecord, RouteImportRecord, StationImportRecord


@dataclass(slots=True)
class DarwinScheduleInfo:
    rid: str
    service_date: date
    operator_code: str | None
    origin_tpl: str
    destination_tpl: str
    scheduled_departure: datetime
    scheduled_arrival: datetime

    @property
    def route_name(self) -> str:
        return f"{self.origin_tpl} to {self.destination_tpl}"

    @property
    def route_code(self) -> str:
        return f"{self.origin_tpl}-{self.destination_tpl}"


@dataclass(slots=True)
class DarwinImportBundle:
    station_records: list[StationImportRecord]
    route_records: list[RouteImportRecord]
    journey_records: list[JourneyImportRecord]


class DarwinSnapshotService:
    """Fetches and normalizes Darwin snapshot data for local ingestion."""

    def fetch_latest_snapshot(
        self,
        host: str,
        username: str,
        password: str,
        remote_directory: str,
        download_directory: str | Path,
    ) -> Path:
        target_dir = Path(download_directory)
        target_dir.mkdir(parents=True, exist_ok=True)

        ftp = FTP(host, timeout=30)
        ftp.login(username, password)
        ftp.cwd(remote_directory)
        names = ftp.nlst()

        snapshot_name = self._pick_snapshot_name(names)
        local_path = target_dir / Path(snapshot_name).name
        with local_path.open("wb") as handle:
            ftp.retrbinary(f"RETR {snapshot_name}", handle.write)
        ftp.quit()
        return local_path

    def build_import_bundle(
        self,
        snapshot_path: str | Path,
        max_services: int | None = None,
    ) -> DarwinImportBundle:
        path = Path(snapshot_path)
        schedules = self._load_schedules(path)
        station_records = self._build_station_records(schedules.values())
        route_records = self._build_route_records(schedules.values())
        journey_records = self._build_journey_records(path, schedules, max_services=max_services)
        return DarwinImportBundle(
            station_records=station_records,
            route_records=route_records,
            journey_records=journey_records,
        )

    def _pick_snapshot_name(self, names: list[str]) -> str:
        gz_names = sorted(name for name in names if name.lower().endswith(".gz"))
        if gz_names:
            return gz_names[-1]

        xml_names = sorted(name for name in names if name.lower().endswith(".xml"))
        if xml_names:
            return xml_names[-1]

        if not names:
            raise ValueError("no Darwin snapshot files found")
        return sorted(names)[-1]

    def _load_schedules(self, snapshot_path: Path) -> dict[tuple[str, date], DarwinScheduleInfo]:
        schedules: dict[tuple[str, date], DarwinScheduleInfo] = {}
        for document in self._iter_xml_documents(snapshot_path):
            root = self._parse_xml_document(document)
            if root is None:
                continue

            for schedule_element in root.findall(".//{*}schedule"):
                info = self._parse_schedule(schedule_element)
                if info is not None:
                    schedules[(info.rid, info.service_date)] = info
        return schedules

    def _build_station_records(
        self,
        schedules: list[DarwinScheduleInfo] | tuple[DarwinScheduleInfo, ...] | object,
    ) -> list[StationImportRecord]:
        unique_codes: set[str] = set()
        records: list[StationImportRecord] = []
        for schedule in schedules:
            for code in (schedule.origin_tpl, schedule.destination_tpl):
                if code in unique_codes:
                    continue
                unique_codes.add(code)
                records.append(StationImportRecord(name=code, code=code))
        records.sort(key=lambda record: record.code or record.name)
        return records

    def _build_route_records(
        self,
        schedules: list[DarwinScheduleInfo] | tuple[DarwinScheduleInfo, ...] | object,
    ) -> list[RouteImportRecord]:
        unique_routes: dict[str, RouteImportRecord] = {}
        for schedule in schedules:
            unique_routes.setdefault(
                schedule.route_code,
                RouteImportRecord(
                    origin_station_code=schedule.origin_tpl,
                    destination_station_code=schedule.destination_tpl,
                    name=schedule.route_name,
                    code=schedule.route_code,
                    operator_name=schedule.operator_code,
                    is_active=True,
                ),
            )
        return list(unique_routes.values())

    def _build_journey_records(
        self,
        snapshot_path: Path,
        schedules: dict[tuple[str, date], DarwinScheduleInfo],
        max_services: int | None = None,
    ) -> list[JourneyImportRecord]:
        journey_records: list[JourneyImportRecord] = []
        for document in self._iter_xml_documents(snapshot_path):
            root = self._parse_xml_document(document)
            if root is None:
                continue

            for service_element in root.findall(".//{*}TS"):
                record = self._parse_train_status(service_element, schedules)
                if record is None:
                    continue
                journey_records.append(record)
                if max_services is not None and len(journey_records) >= max_services:
                    return journey_records
        return journey_records

    def _iter_xml_documents(self, snapshot_path: Path):
        opener = gzip.open if snapshot_path.suffix.lower() == ".gz" else Path.open
        with opener(snapshot_path, "rt", encoding="utf-8", errors="ignore") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue

                if line.count("<?xml") <= 1:
                    yield line
                    continue

                parts = line.split("<?xml")
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    yield part if part.startswith("<?xml") else f"<?xml{part}"

    def _parse_xml_document(self, xml_text: str):
        try:
            return ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            return None

    def _parse_schedule(self, element) -> DarwinScheduleInfo | None:
        rid = element.attrib.get("rid")
        ssd = element.attrib.get("ssd")
        if not rid or not ssd:
            return None

        service_date = date.fromisoformat(ssd)
        locations = [child for child in list(element) if "tpl" in child.attrib]
        if len(locations) < 2:
            return None

        origin = locations[0]
        destination = locations[-1]
        origin_tpl = origin.attrib.get("tpl")
        destination_tpl = destination.attrib.get("tpl")
        departure_text = origin.attrib.get("ptd") or origin.attrib.get("wtd")
        arrival_text = destination.attrib.get("pta") or destination.attrib.get("wta")

        if not origin_tpl or not destination_tpl or not departure_text or not arrival_text:
            return None

        scheduled_departure = self._combine_service_time(service_date, departure_text)
        scheduled_arrival = self._combine_service_time(service_date, arrival_text)
        if scheduled_arrival < scheduled_departure:
            scheduled_arrival += timedelta(days=1)

        return DarwinScheduleInfo(
            rid=rid,
            service_date=service_date,
            operator_code=element.attrib.get("toc"),
            origin_tpl=origin_tpl,
            destination_tpl=destination_tpl,
            scheduled_departure=scheduled_departure,
            scheduled_arrival=scheduled_arrival,
        )

    def _parse_train_status(
        self,
        element,
        schedules: dict[tuple[str, date], DarwinScheduleInfo],
    ) -> JourneyImportRecord | None:
        rid = element.attrib.get("rid")
        ssd = element.attrib.get("ssd")
        if not rid or not ssd:
            return None

        service_date = date.fromisoformat(ssd)
        schedule = schedules.get((rid, service_date))
        locations = [child for child in list(element) if self._local_name(child.tag) == "Location"]
        if len(locations) < 2:
            return None

        first_location = locations[0]
        last_location = locations[-1]
        origin_tpl = schedule.origin_tpl if schedule is not None else first_location.attrib.get("tpl")
        destination_tpl = (
            schedule.destination_tpl if schedule is not None else last_location.attrib.get("tpl")
        )
        if not origin_tpl or not destination_tpl:
            return None

        scheduled_departure = (
            schedule.scheduled_departure
            if schedule is not None
            else self._combine_service_time(
                service_date,
                first_location.attrib.get("ptd") or first_location.attrib.get("wtd"),
            )
        )
        scheduled_arrival = (
            schedule.scheduled_arrival
            if schedule is not None
            else self._combine_service_time(
                service_date,
                last_location.attrib.get("pta") or last_location.attrib.get("wta"),
            )
        )
        if scheduled_departure is None or scheduled_arrival is None:
            return None

        actual_departure = self._extract_actual_time(service_date, first_location, "dep")
        actual_arrival = self._extract_actual_time(service_date, last_location, "arr")
        if actual_arrival is not None and actual_arrival < scheduled_departure:
            actual_arrival += timedelta(days=1)
        if actual_departure is not None and actual_departure < scheduled_departure - timedelta(hours=6):
            actual_departure += timedelta(days=1)

        return JourneyImportRecord(
            route_code=schedule.route_code if schedule is not None else f"{origin_tpl}-{destination_tpl}",
            origin_station_code=origin_tpl,
            destination_station_code=destination_tpl,
            route_name=schedule.route_name if schedule is not None else f"{origin_tpl} to {destination_tpl}",
            operator_name=schedule.operator_code if schedule is not None else None,
            journey_date=service_date,
            scheduled_departure=scheduled_departure,
            actual_departure=actual_departure,
            scheduled_arrival=scheduled_arrival,
            actual_arrival=actual_arrival,
            reason_for_delay=self._extract_delay_reason(element),
            source="darwin_snapshot",
            external_service_id=rid,
        )

    def _extract_actual_time(self, service_date: date, location, event_name: str) -> datetime | None:
        for child in list(location):
            if self._local_name(child.tag) != event_name:
                continue
            for attribute_name in ("at", "et", "wet"):
                value = child.attrib.get(attribute_name)
                if value:
                    return self._combine_service_time(service_date, value)
        return None

    def _extract_delay_reason(self, element) -> str | None:
        for child in element.iter():
            local_name = self._local_name(child.tag).lower()
            if "reason" in local_name:
                text = (child.text or "").strip()
                if text:
                    return text
        return None

    def _combine_service_time(self, service_date: date, value: str | None) -> datetime | None:
        if value is None:
            return None

        parts = value.split(":")
        if len(parts) == 2:
            hour, minute = parts
            second = "0"
        elif len(parts) == 3:
            hour, minute, second = parts
        else:
            return None

        clock_time = time(int(hour), int(minute), int(second))
        return datetime.combine(service_date, clock_time)

    def _local_name(self, tag: str) -> str:
        return tag.split("}", 1)[1] if "}" in tag else tag
