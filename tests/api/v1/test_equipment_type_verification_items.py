_ids: dict = {}


def _setup(client, auth_headers) -> dict:
    if _ids:
        return _ids

    et = client.post(
        "/api/v1/equipment-types/",
        json={
            "name": "VerifItemTest Type",
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

    vt = client.post(
        f"/api/v1/equipment-type-verifications/equipment-type/{_ids['equipment_type_id']}",
        json={"name": "Verificación Semanal", "frequency_days": 7, "is_active": True},
        headers=auth_headers,
    )
    assert vt.status_code == 201
    _ids["verification_type_id"] = vt.json()["id"]

    return _ids


# ---------------------------------------------------------------------------
# POST /equipment-type-verification-items/equipment-type/{id}
# ---------------------------------------------------------------------------


def test_create_verification_item(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}",
        json={
            "item": "Verificar cero",
            "response_type": "boolean",
            "is_required": True,
            "order": 1,
            "expected_bool": True,
            "verification_type_id": ids["verification_type_id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item"] == "Verificar cero"
    assert data["response_type"] == "boolean"
    _ids["item_id"] = data["id"]


def test_create_verification_item_invalid_verification_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}",
        json={
            "item": "Test",
            "response_type": "boolean",
            "is_required": False,
            "order": 1,
            "verification_type_id": 999999,
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_verification_item_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        "/api/v1/equipment-type-verification-items/equipment-type/999999",
        json={
            "item": "Test",
            "response_type": "boolean",
            "is_required": False,
            "order": 1,
            "verification_type_id": ids["verification_type_id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_verification_item_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}",
        json={
            "item": "Test",
            "response_type": "boolean",
            "is_required": False,
            "order": 1,
            "verification_type_id": ids["verification_type_id"],
        },
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST .../bulk
# ---------------------------------------------------------------------------


def test_create_verification_items_bulk(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}/bulk",
        json={
            "items": [
                {
                    "item": "Lectura alta",
                    "response_type": "number",
                    "is_required": False,
                    "order": 20,
                    "verification_type_id": ids["verification_type_id"],
                },
                {
                    "item": "Lectura baja",
                    "response_type": "number",
                    "is_required": False,
                    "order": 21,
                    "verification_type_id": ids["verification_type_id"],
                },
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# GET /equipment-type-verification-items/equipment-type/{id}
# ---------------------------------------------------------------------------


def test_list_verification_items(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_verification_items_filter_by_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}",
        params={"verification_type_id": ids["verification_type_id"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_list_verification_items_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-type-verification-items/equipment-type/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /equipment-type-verification-items/equipment-type/{type_id}/{item_id}
# ---------------------------------------------------------------------------


def test_update_verification_item(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "item_id" in ids
    response = client.put(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}/{ids['item_id']}",
        json={"item": "Verificar cero (actualizado)", "is_required": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["item"] == "Verificar cero (actualizado)"


def test_update_verification_item_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.put(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}/999999",
        json={"item": "No existe"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /equipment-type-verification-items/equipment-type/{type_id}/{item_id}
# ---------------------------------------------------------------------------


def test_delete_verification_item(client, auth_headers):
    ids = _setup(client, auth_headers)
    create = client.post(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}",
        json={
            "item": "Item a borrar",
            "response_type": "boolean",
            "is_required": False,
            "order": 99,
            "verification_type_id": ids["verification_type_id"],
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    response = client.delete(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}/{item_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == item_id


def test_delete_verification_item_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.delete(
        f"/api/v1/equipment-type-verification-items/equipment-type/{ids['equipment_type_id']}/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404
