_ids: dict = {}


def _setup(client, auth_headers) -> dict:
    if _ids:
        return _ids

    et = client.post(
        "/api/v1/equipment-types/",
        json={
            "name": "VerifTypeTest Type",
            "role": "working",
            "calibration_days": 180,
            "maintenance_days": 90,
            "inspection_days": 30,
            "measures": ["temperature"],
            "max_errors": [
                {"measure": "temperature", "max_error_value": 0.5, "unit": "C"}
            ],
        },
        headers=auth_headers,
    )
    assert et.status_code == 201
    _ids["equipment_type_id"] = et.json()["id"]
    return _ids


# ---------------------------------------------------------------------------
# POST /equipment-type-verifications/equipment-type/{id}
# ---------------------------------------------------------------------------


def test_create_verification_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}",
        json={"name": "Verificación Diaria", "frequency_days": 1, "is_active": True, "order": 0},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Verificación Diaria"
    assert data["frequency_days"] == 1
    assert data["is_active"] is True
    _ids["verification_type_id"] = data["id"]


def test_create_verification_type_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/equipment-type-verifications/equipment-type/999999",
        json={"name": "Verif Test", "frequency_days": 7},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_verification_type_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}",
        json={"name": "No Auth", "frequency_days": 7},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment-type-verifications/equipment-type/{id}
# ---------------------------------------------------------------------------


def test_list_verification_types(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_verification_types_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-type-verifications/equipment-type/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_verification_types_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}",
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PUT /equipment-type-verifications/equipment-type/{type_id}/{verification_type_id}
# ---------------------------------------------------------------------------


def test_update_verification_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "verification_type_id" in ids
    response = client.put(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}/{ids['verification_type_id']}",
        json={"name": "Verificación Diaria (actualizada)", "frequency_days": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["frequency_days"] == 2


def test_update_verification_type_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.put(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}/999999",
        json={"name": "No existe"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /equipment-type-verifications/equipment-type/{type_id}/{verification_type_id}
# ---------------------------------------------------------------------------


def test_delete_verification_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Create a disposable verification type to delete
    create = client.post(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}",
        json={"name": "Verif a borrar", "frequency_days": 99},
        headers=auth_headers,
    )
    assert create.status_code == 201
    vt_id = create.json()["id"]

    response = client.delete(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}/{vt_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == vt_id


def test_delete_verification_type_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.delete(
        f"/api/v1/equipment-type-verifications/equipment-type/{ids['equipment_type_id']}/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404
