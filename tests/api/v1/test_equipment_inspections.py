"""
Tests for equipment inspections.

Setup requires:
  - Equipment type with calibration_days=0 (no expiry)
  - At least one inspection item (required)
  - Equipment with a valid calibration
"""

_ids: dict = {}


def _setup(client, auth_headers) -> dict:
    if _ids:
        return _ids

    me = client.get("/api/v1/users/me", headers=auth_headers).json()
    company_id = me["company_id"]

    et = client.post(
        "/api/v1/equipment-types/",
        json={
            "name": "InspTest Thermometer",
            "role": "working",
            "calibration_days": 0,
            "maintenance_days": 90,
            "inspection_days": 0,
            "measures": [],
            "max_errors": [],
        },
        headers=auth_headers,
    )
    assert et.status_code == 201
    eq_type_id = et.json()["id"]

    # Create inspection items for this type
    item_bool = client.post(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{eq_type_id}",
        json={
            "item": "Pantalla funcional",
            "response_type": "boolean",
            "is_required": True,
            "order": 1,
            "expected_bool": True,
        },
        headers=auth_headers,
    )
    assert item_bool.status_code == 201
    item_bool_id = item_bool.json()["id"]

    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "InspTest Block", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert block.status_code == 201

    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "InspTest Admin Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert admin_co.status_code == 201

    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "InspTest Terminal",
            "terminal_code": "INST",
            "is_active": True,
            "has_lab": True,
            "block_id": block.json()["id"],
            "owner_company_id": company_id,
            "admin_company_id": admin_co.json()["id"],
        },
        headers=auth_headers,
    )
    assert terminal.status_code == 201

    eq = client.post(
        "/api/v1/equipment/",
        json={
            "serial": "INSP-SN-001",
            "model": "InspModel",
            "brand": "InspBrand",
            "equipment_type_id": eq_type_id,
            "owner_company_id": company_id,
            "terminal_id": terminal.json()["id"],
        },
        headers=auth_headers,
    )
    assert eq.status_code == 201
    equipment_id = eq.json()["id"]

    # Create a valid calibration so inspection is allowed
    calib = client.post(
        f"/api/v1/equipment-calibrations/equipment/{equipment_id}",
        json={
            "calibration_company_id": company_id,
            "certificate_number": "INSP-CERT-001",
            "calibrated_at": "2024-01-01T00:00:00",
            "results": [],
        },
        headers=auth_headers,
    )
    assert calib.status_code == 201

    _ids.update(
        {
            "company_id": company_id,
            "eq_type_id": eq_type_id,
            "terminal_id": terminal.json()["id"],
            "equipment_id": equipment_id,
            "item_bool_id": item_bool_id,
        }
    )
    return _ids


def _ok_inspection_payload(ids: dict, date: str = "2024-03-01T08:00:00") -> dict:
    return {
        "inspected_at": date,
        "notes": "Todo OK",
        "responses": [
            {
                "inspection_item_id": ids["item_bool_id"],
                "response_type": "boolean",
                "value_bool": True,
            }
        ],
    }


# ---------------------------------------------------------------------------
# POST /equipment-inspections/equipment/{id}
# ---------------------------------------------------------------------------


def test_create_inspection(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json=_ok_inspection_payload(ids),
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["equipment_id"] == ids["equipment_id"]
    assert data["is_ok"] is True
    assert len(data["responses"]) == 1
    _ids["inspection_id"] = data["id"]


def test_create_inspection_equipment_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        "/api/v1/equipment-inspections/equipment/999999",
        json=_ok_inspection_payload(ids),
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_inspection_future_date(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json=_ok_inspection_payload(ids, date="2099-01-01T08:00:00"),
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_inspection_missing_required_item(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json={
            "inspected_at": "2024-03-05T08:00:00",
            "responses": [],
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_inspection_wrong_response_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json={
            "inspected_at": "2024-03-06T08:00:00",
            "responses": [
                {
                    "inspection_item_id": ids["item_bool_id"],
                    "response_type": "number",  # wrong — item expects boolean
                    "value_number": 1.0,
                }
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_inspection_duplicate_item_id(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json={
            "inspected_at": "2024-03-07T08:00:00",
            "responses": [
                {
                    "inspection_item_id": ids["item_bool_id"],
                    "response_type": "boolean",
                    "value_bool": True,
                },
                {
                    "inspection_item_id": ids["item_bool_id"],
                    "response_type": "boolean",
                    "value_bool": False,
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_inspection_same_day_conflict(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Same date as test_create_inspection (2024-03-01)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json=_ok_inspection_payload(ids, date="2024-03-01T10:00:00"),
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_create_inspection_replace_existing(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Replace the same-day inspection from previous test
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}?replace_existing=true",
        json=_ok_inspection_payload(ids, date="2024-03-01T12:00:00"),
        headers=auth_headers,
    )
    assert response.status_code == 201
    _ids["inspection_id"] = response.json()["id"]


def test_create_inspection_failed_sets_needs_review(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json={
            "inspected_at": "2024-04-01T08:00:00",
            "responses": [
                {
                    "inspection_item_id": ids["item_bool_id"],
                    "response_type": "boolean",
                    "value_bool": False,  # expected True → is_ok=False
                }
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["is_ok"] is False
    assert "needs_review" in (data.get("message") or "")


def test_create_inspection_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        json=_ok_inspection_payload(ids, date="2024-05-01T08:00:00"),
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment-inspections/equipment/{id}
# ---------------------------------------------------------------------------


def test_list_inspections(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-inspections/equipment/{ids['equipment_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_inspections_equipment_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-inspections/equipment/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /equipment-inspections/{inspection_id}
# ---------------------------------------------------------------------------


def test_get_inspection_by_id(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "inspection_id" in ids
    response = client.get(
        f"/api/v1/equipment-inspections/{ids['inspection_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ids["inspection_id"]
    assert "responses" in data


def test_get_inspection_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-inspections/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /equipment-inspections/{inspection_id}
# ---------------------------------------------------------------------------


def test_update_inspection(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "inspection_id" in ids
    response = client.patch(
        f"/api/v1/equipment-inspections/{ids['inspection_id']}",
        json={
            "inspected_at": "2024-03-01T09:00:00",
            "notes": "Actualizado",
            "responses": [
                {
                    "inspection_item_id": ids["item_bool_id"],
                    "response_type": "boolean",
                    "value_bool": True,
                }
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Actualizado"


def test_update_inspection_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.patch(
        "/api/v1/equipment-inspections/999999",
        json={
            "responses": [
                {
                    "inspection_item_id": ids["item_bool_id"],
                    "response_type": "boolean",
                    "value_bool": True,
                }
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
