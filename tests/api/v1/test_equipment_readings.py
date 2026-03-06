"""
Tests for equipment readings (temperature).

Setup requires:
  - Equipment type with inspection_days=0 (no inspection required before reading)
    and calibration_days=0
  - Equipment with status in_use (achieved via a successful inspection)
  - Valid calibration
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
            "name": "ReadTest Thermometer",
            "role": "working",
            "calibration_days": 0,
            "maintenance_days": 90,
            "inspection_days": 0,  # skip inspection window check
            "measures": [],
            "max_errors": [],
        },
        headers=auth_headers,
    )
    assert et.status_code == 201
    eq_type_id = et.json()["id"]

    # Inspection item so we can create a passing inspection → status in_use
    item = client.post(
        f"/api/v1/equipment-type-inspection-items/equipment-type/{eq_type_id}",
        json={
            "item": "Encendido correcto",
            "response_type": "boolean",
            "is_required": True,
            "order": 1,
            "expected_bool": True,
        },
        headers=auth_headers,
    )
    assert item.status_code == 201
    item_id = item.json()["id"]

    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "ReadTest Block", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert block.status_code == 201

    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "ReadTest Admin Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert admin_co.status_code == 201

    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "ReadTest Terminal",
            "terminal_code": "RDTS",
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
            "serial": "READ-SN-001",
            "model": "ReadModel",
            "brand": "ReadBrand",
            "equipment_type_id": eq_type_id,
            "owner_company_id": company_id,
            "terminal_id": terminal.json()["id"],
        },
        headers=auth_headers,
    )
    assert eq.status_code == 201
    equipment_id = eq.json()["id"]

    # Valid calibration
    calib = client.post(
        f"/api/v1/equipment-calibrations/equipment/{equipment_id}",
        json={
            "calibration_company_id": company_id,
            "certificate_number": "READ-CERT-001",
            "calibrated_at": "2024-01-01T00:00:00",
            "results": [],
        },
        headers=auth_headers,
    )
    assert calib.status_code == 201

    # Passing inspection → status becomes in_use
    insp = client.post(
        f"/api/v1/equipment-inspections/equipment/{equipment_id}",
        json={
            "inspected_at": "2024-03-01T08:00:00",
            "responses": [
                {
                    "inspection_item_id": item_id,
                    "response_type": "boolean",
                    "value_bool": True,
                }
            ],
        },
        headers=auth_headers,
    )
    assert insp.status_code == 201
    assert insp.json()["is_ok"] is True

    _ids.update(
        {
            "company_id": company_id,
            "eq_type_id": eq_type_id,
            "terminal_id": terminal.json()["id"],
            "equipment_id": equipment_id,
        }
    )
    return _ids


# ---------------------------------------------------------------------------
# POST /equipment-readings/equipment/{id}
# ---------------------------------------------------------------------------


def test_create_reading(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-readings/equipment/{ids['equipment_id']}",
        json={"value": 20.0, "unit": "C"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["equipment_id"] == ids["equipment_id"]
    assert data["value_celsius"] == 20.0
    _ids["reading_id"] = data["id"]


def test_create_reading_fahrenheit_converted(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-readings/equipment/{ids['equipment_id']}",
        json={"value": 68.0, "unit": "F"},  # 68°F = 20°C
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert abs(data["value_celsius"] - 20.0) < 0.01


def test_create_reading_unsupported_unit(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-readings/equipment/{ids['equipment_id']}",
        json={"value": 20.0, "unit": "INVALID"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_reading_equipment_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/equipment-readings/equipment/999999",
        json={"value": 20.0, "unit": "C"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_reading_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-readings/equipment/{ids['equipment_id']}",
        json={"value": 20.0, "unit": "C"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment-readings/equipment/{id}
# ---------------------------------------------------------------------------


def test_list_readings(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-readings/equipment/{ids['equipment_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_readings_equipment_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-readings/equipment/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_readings_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-readings/equipment/{ids['equipment_id']}",
    )
    assert response.status_code == 401
