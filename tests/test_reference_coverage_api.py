from app.models.route import Route
from app.models.station import Station


def test_route_name_coverage_endpoint(client, db_session) -> None:
    resolved_origin = Station(name="London Waterloo", code="WAT", crs_code="WAT")
    resolved_destination = Station(name="Exeter St Davids", code="EXD", crs_code="EXD")
    unresolved_origin = Station(name="WMBYLCS", code="WMBYLCS", tiploc_code="WMBYLCS")
    unresolved_destination = Station(name="CLPHMJC", code="CLPHMJC", tiploc_code="CLPHMJC")
    db_session.add_all(
        [resolved_origin, resolved_destination, unresolved_origin, unresolved_destination]
    )
    db_session.flush()

    db_session.add_all(
        [
            Route(
                origin_station_id=resolved_origin.id,
                destination_station_id=resolved_destination.id,
                name="London Waterloo to Exeter St Davids",
                code="WAT-EXD",
                operator_name="SW",
                is_active=True,
            ),
            Route(
                origin_station_id=resolved_origin.id,
                destination_station_id=unresolved_destination.id,
                name="London Waterloo to CLPHMJC",
                code="WAT-CLPHMJC",
                operator_name="SW",
                is_active=True,
            ),
            Route(
                origin_station_id=unresolved_origin.id,
                destination_station_id=unresolved_destination.id,
                name="WMBYLCS to CLPHMJC",
                code="WMBYLCS-CLPHMJC",
                operator_name="SW",
                is_active=True,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/analytics/reference-data/route-name-coverage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_routes"] == 3
    assert payload["fully_human_readable_routes"] == 1
    assert payload["partially_unresolved_routes"] == 1
    assert payload["fully_unresolved_routes"] == 1
    assert payload["unresolved_location_count"] == 2
    assert payload["top_unresolved_locations"][0]["station_name"] == "CLPHMJC"
