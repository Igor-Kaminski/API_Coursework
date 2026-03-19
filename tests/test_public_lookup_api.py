def test_station_lookup_by_code(client, seeded_reference_data) -> None:
    response = client.get("/api/v1/stations/code/LDS")

    assert response.status_code == 200
    assert response.json()["code"] == "LDS"
    assert response.json()["name"] == "Leeds"


def test_station_list_can_filter_by_code(client, seeded_reference_data) -> None:
    response = client.get("/api/v1/stations?code=YRK")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["code"] == "YRK"


def test_route_lookup_by_code(client, seeded_reference_data) -> None:
    response = client.get("/api/v1/routes/code/LDS-YRK")

    assert response.status_code == 200
    assert response.json()["code"] == "LDS-YRK"
    assert response.json()["origin_station"]["code"] == "LDS"
    assert response.json()["destination_station"]["code"] == "YRK"


def test_route_list_can_filter_by_origin_destination_and_name(client, seeded_reference_data) -> None:
    by_stations = client.get("/api/v1/routes?origin=LDS&destination=YRK")
    by_name = client.get("/api/v1/routes?name=leeds to york")

    assert by_stations.status_code == 200
    assert len(by_stations.json()) == 1
    assert by_stations.json()[0]["code"] == "LDS-YRK"

    assert by_name.status_code == 200
    assert len(by_name.json()) == 1
    assert by_name.json()[0]["name"] == "Leeds to York"
