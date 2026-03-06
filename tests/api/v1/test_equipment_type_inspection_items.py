_ids: dict = {}


def _setup(client, auth_headers) -> dict:
    if _ids:
        return _ids

    et = client.post(
        "/api/v1/equipment-types/",
        json={
            "name": "InspItemTest Type",
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
# POST /equipment-type-inspection-items/equipment-type/{id}
# ---------------------------------------------------------------------------


def test_create_inspection_item(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}",
        json={
            "item": "Verificar pantalla",
            "response_type": "boolean",
            "is_required": True,
            "order": 1,
            "expected_bool": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item"] == "Verificar pantalla"
    assert data["response_type"] == "boolean"
    assert data["is_required"] is True
    assert data["expected_bool"] is True
    _ids["item_id"] = data["id"]


def test_create_inspection_item_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/equipment-type-inspection-items/equipment-type/999999",
        json={"item": "Test item", "response_type": "boolean", "is_required": False, "order": 1},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_inspection_item_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}",
        json={"item": "Test item", "response_type": "boolean", "is_required": False, "order": 1},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST .../bulk
# ---------------------------------------------------------------------------


def test_create_inspection_items_bulk(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}/bulk",
        json={
            "items": [
                {"item": "Item texto 1", "response_type": "text", "is_required": False, "order": 10},
                {"item": "Item número 1", "response_type": "number", "is_required": False, "order": 11,
                 "expected_number_min": 0.0, "expected_number_max": 100.0},
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 2


def test_create_inspection_items_bulk_empty(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}/bulk",
        json={"items": []},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data.get("message") == "No records found"


# ---------------------------------------------------------------------------
# GET /equipment-type-inspection-items/equipment-type/{id}
# ---------------------------------------------------------------------------


def test_list_inspection_items(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_inspection_items_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-type-inspection-items/equipment-type/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_inspection_items_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}",
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PUT /equipment-type-inspection-items/equipment-type/{type_id}/{item_id}
# ---------------------------------------------------------------------------


def test_update_inspection_item(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "item_id" in ids, "test_create_inspection_item must run first"
    response = client.put(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}/{ids['item_id']}",
        json={"item": "Verificar pantalla (actualizado)", "is_required": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["item"] == "Verificar pantalla (actualizado)"


def test_update_inspection_item_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.put(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}/999999",
        json={"item": "No existe"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /equipment-type-inspection-items/equipment-type/{type_id}/{item_id}
# ---------------------------------------------------------------------------


def test_delete_inspection_item(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Create a disposable item to delete
    create = client.post(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}",
        json={"item": "Item a borrar", "response_type": "boolean", "is_required": False, "order": 99},
        headers=auth_headers,
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    response = client.delete(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}/{item_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == item_id


def test_delete_inspection_item_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.delete(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{ids['equipment_type_id']}/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404
