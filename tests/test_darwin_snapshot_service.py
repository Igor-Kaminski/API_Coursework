import gzip
from pathlib import Path

from app.services.darwin_snapshot_service import DarwinSnapshotService


SCHEDULE_DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Pport xmlns="http://www.thalesgroup.com/rtti/PushPort/v16" xmlns:ns2="http://www.thalesgroup.com/rtti/PushPort/Schedules/v3"><sR><schedule rid="202603197972291" uid="O72291" trainId="1L65" ssd="2026-03-19" toc="SW" trainCat="XX"><ns2:OR wtd="20:20" tpl="WATRLMN" act="TB" ptd="20:20"/><ns2:IP wta="20:44:30" wtd="20:46:30" tpl="WOKING" act="T " pta="20:45" ptd="20:46"/><ns2:DT wta="23:45" pta="23:45" tpl="EXETRSD" act="TF"/></schedule></sR></Pport>"""

TS_DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Pport xmlns="http://www.thalesgroup.com/rtti/PushPort/v16" xmlns:ns5="http://www.thalesgroup.com/rtti/PushPort/Forecasts/v3"><sR><TS rid="202603197972291" uid="O72291" ssd="2026-03-19"><ns5:Location tpl="WATRLMN" wtd="20:20" ptd="20:20"><ns5:dep et="20:21" src="Darwin"/></ns5:Location><ns5:Location tpl="WOKING" wta="20:44:30" wtd="20:46:30" pta="20:45" ptd="20:46"><ns5:arr et="20:45" wet="20:44" src="Darwin"/><ns5:dep et="20:46" src="Darwin"/></ns5:Location><ns5:Location tpl="EXETRSD" wta="23:45" pta="23:45"><ns5:arr et="23:47" src="Darwin"/></ns5:Location></TS></sR></Pport>"""


def test_build_import_bundle_from_snapshot_lines(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.gz"
    with gzip.open(snapshot_path, "wt", encoding="utf-8") as handle:
        handle.write(SCHEDULE_DOC + "\n")
        handle.write(TS_DOC + "\n")

    service = DarwinSnapshotService()
    bundle = service.build_import_bundle(snapshot_path)

    assert len(bundle.station_records) == 2
    assert {record.tiploc_code for record in bundle.station_records} == {"WATRLMN", "EXETRSD"}
    assert {record.code for record in bundle.station_records} == {None}

    assert len(bundle.route_records) == 1
    route = bundle.route_records[0]
    assert route.origin_station_code == "WATRLMN"
    assert route.destination_station_code == "EXETRSD"
    assert route.code == "WATRLMN-EXETRSD"
    assert route.operator_name == "SW"

    assert len(bundle.journey_records) == 1
    journey = bundle.journey_records[0]
    assert journey.external_service_id == "202603197972291"
    assert journey.origin_station_code == "WATRLMN"
    assert journey.destination_station_code == "EXETRSD"
    assert journey.route_code == "WATRLMN-EXETRSD"
    assert journey.scheduled_departure.isoformat() == "2026-03-19T20:20:00"
    assert journey.actual_departure.isoformat() == "2026-03-19T20:21:00"
    assert journey.scheduled_arrival.isoformat() == "2026-03-19T23:45:00"
    assert journey.actual_arrival.isoformat() == "2026-03-19T23:47:00"
