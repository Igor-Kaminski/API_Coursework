from app.models.route import Route
from app.models.station import Station
from app.services.dtd_reference_service import DTDReferenceService


MSN_CONTENT = """A    LONDON WATERLOO               3WATRLMNWAT   WAT15312 6179815                 
A    EXETER ST DAVIDS              2EXETRSDEXD   EXD12911 60933 6                 
A    ABERDARE                      0ABDARE ABA   ABA13004 62027 3                 
"""


def test_dtd_reference_service_updates_tiploc_rows_and_route_names(db_session) -> None:
    duplicate = Station(name="Aberdare", code="ABA")
    db_session.add(duplicate)

    origin = Station(name="WATRLMN", code="WATRLMN", tiploc_code=None)
    destination = Station(name="EXETRSD", code="EXETRSD", tiploc_code=None)
    aberdare_tiploc = Station(name="ABDARE", code="ABDARE", tiploc_code=None)
    db_session.add_all([origin, destination, aberdare_tiploc])
    db_session.flush()

    route = Route(
        origin_station_id=origin.id,
        destination_station_id=destination.id,
        name="WATRLMN to EXETRSD",
        code="WATRLMN-EXETRSD",
        operator_name="SW",
        is_active=True,
    )
    db_session.add(route)
    db_session.commit()

    service = DTDReferenceService()
    records = service._parse_msn_records(MSN_CONTENT)
    station_result, renamed_routes = service.enrich_database(db_session, records)

    db_session.refresh(origin)
    db_session.refresh(destination)
    db_session.refresh(route)

    assert station_result.updated == 3
    assert origin.name == "London Waterloo"
    assert origin.code == "WAT"
    assert origin.tiploc_code == "WATRLMN"
    assert origin.crs_code == "WAT"
    assert destination.name == "Exeter St Davids"
    assert destination.code == "EXD"
    assert destination.tiploc_code == "EXETRSD"
    assert renamed_routes == 1
    assert route.name == "London Waterloo to Exeter St Davids"
    db_session.refresh(duplicate)
    assert duplicate.name == "Aberdare"
    assert duplicate.code == "ABA"
    assert duplicate.tiploc_code == "ABDARE"
    assert db_session.get(Station, aberdare_tiploc.id) is None


def test_dtd_reference_service_collapses_alias_tiplocs_by_crs(db_session) -> None:
    alias_one = Station(name="BCKNBUS", code="BCKNBUS", tiploc_code=None)
    alias_two = Station(name="BCKNHMJ", code="BCKNHMJ", tiploc_code=None)
    canonical = Station(name="Beckenham Junction", code="BKJ")
    db_session.add_all([alias_one, alias_two, canonical])
    db_session.flush()

    route = Route(
        origin_station_id=alias_one.id,
        destination_station_id=alias_two.id,
        name="BCKNBUS to BCKNHMJ",
        code="BCKNBUS-BCKNHMJ",
        operator_name="SE",
        is_active=True,
    )
    db_session.add(route)
    db_session.commit()

    service = DTDReferenceService()
    records = service._parse_msn_records(
        "A    BECKENHAM JUNCTION            9BCKNBUSBKJ   BKJ15373 61699 5                 \n"
        "A    BECKENHAM JUNCTION            2BCKNHMJBKJ   BKJ15373 61699 5                 \n"
    )
    station_result, renamed_routes = service.enrich_database(db_session, records)

    db_session.refresh(canonical)
    db_session.refresh(route)

    assert station_result.updated == 1
    assert db_session.get(Station, alias_one.id) is None
    assert db_session.get(Station, alias_two.id) is None
    assert route.origin_station_id == canonical.id
    assert route.destination_station_id == canonical.id
    assert route.name == "Beckenham Junction to Beckenham Junction"
    assert renamed_routes == 1


def test_dtd_reference_service_backfills_safe_tiploc_for_crs_station(db_session) -> None:
    station = Station(name="Leeds", code="LDS", crs_code="LDS", tiploc_code=None)
    db_session.add(station)
    db_session.commit()

    service = DTDReferenceService()
    records = service._parse_msn_records(
        "A    LEEDS                         2LEEDS  LDS   LDS12345 60000 5                 \n"
    )
    station_result, renamed_routes = service.enrich_database(db_session, records)

    db_session.refresh(station)

    assert station_result.updated == 1
    assert station.tiploc_code == "LEEDS"
    assert renamed_routes == 0
