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
    assert db_session.get(Station, duplicate.id) is None
    assert aberdare_tiploc.name == "Aberdare"
    assert aberdare_tiploc.code == "ABA"
