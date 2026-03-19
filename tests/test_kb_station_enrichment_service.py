from app.models.route import Route
from app.models.station import Station
from app.services.kb_station_enrichment_service import KBStationEnrichmentService


KB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Stations>
  <Station>
    <StationName>Woking</StationName>
    <CrsCode>WOK</CrsCode>
    <TiplocCode>WOKING</TiplocCode>
    <LocalityName>Woking</LocalityName>
    <Latitude>51.3198</Latitude>
    <Longitude>-0.5569</Longitude>
  </Station>
</Stations>
"""


def test_kb_enrichment_updates_station_and_route_name(db_session) -> None:
    origin = Station(name="WOKING", code="WOKING")
    destination = Station(name="EXETRSD", code="EXETRSD")
    db_session.add_all([origin, destination])
    db_session.flush()

    route = Route(
        origin_station_id=origin.id,
        destination_station_id=destination.id,
        name="WOKING to EXETRSD",
        code="WOKING-EXETRSD",
        operator_name="SW",
        is_active=True,
    )
    db_session.add(route)
    db_session.commit()

    service = KBStationEnrichmentService()
    records = service.load_records_from_bytes(KB_XML.encode("utf-8"))
    station_result, renamed_routes = service.enrich_database(db_session, records)

    db_session.refresh(origin)
    db_session.refresh(route)

    assert station_result.updated == 1
    assert origin.name == "Woking"
    assert origin.code == "WOK"
    assert origin.tiploc_code == "WOKING"
    assert origin.crs_code == "WOK"
    assert str(origin.latitude) == "51.319800"
    assert str(origin.longitude) == "-0.556900"
    assert renamed_routes == 1
    assert route.name == "Woking to EXETRSD"
