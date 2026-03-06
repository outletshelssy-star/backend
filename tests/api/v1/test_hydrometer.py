def test_calculate_api_60f(client, auth_headers):
    response = client.post(
        "/api/v1/hydrometer/api60f",
        json={"temp_obs_f": 60.0, "lectura_api": 30.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "api_60f" in data
    assert data["message"] == "OK"
    assert isinstance(data["api_60f"], float)


def test_calculate_api_60f_corrects_for_temperature(client, auth_headers):
    r1 = client.post(
        "/api/v1/hydrometer/api60f",
        json={"temp_obs_f": 60.0, "lectura_api": 30.0},
        headers=auth_headers,
    )
    r2 = client.post(
        "/api/v1/hydrometer/api60f",
        json={"temp_obs_f": 80.0, "lectura_api": 30.0},
        headers=auth_headers,
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Correction must differ when temperature differs
    assert r1.json()["api_60f"] != r2.json()["api_60f"]


def test_calculate_api_60f_requires_auth(client):
    response = client.post(
        "/api/v1/hydrometer/api60f",
        json={"temp_obs_f": 60.0, "lectura_api": 30.0},
    )
    assert response.status_code == 401


def test_calculate_api_60f_out_of_range(client, auth_headers):
    # Extreme values that are outside the ASTM table range should return 400
    response = client.post(
        "/api/v1/hydrometer/api60f",
        json={"temp_obs_f": 9999.0, "lectura_api": 9999.0},
        headers=auth_headers,
    )
    assert response.status_code == 400
