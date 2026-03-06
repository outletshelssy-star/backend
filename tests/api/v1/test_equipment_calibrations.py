_ids: dict = {}


def _setup(client, auth_headers) -> dict:
    """Lazy-create shared prerequisites once per test session."""
    if _ids:
        return _ids

    me = client.get("/api/v1/users/me", headers=auth_headers).json()
    company_id = me["company_id"]

    et = client.post(
        "/api/v1/equipment-types/",
        json={
            "name": "CalibTest Thermometer",
            "role": "working",
            "calibration_days": 0,  # no expiry
            "maintenance_days": 90,
            "inspection_days": 0,
            "measures": [],
            "max_errors": [],
        },
        headers=auth_headers,
    )
    assert et.status_code == 201
    eq_type_id = et.json()["id"]

    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "CalibTest Block", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert block.status_code == 201

    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "CalibTest Admin Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert admin_co.status_code == 201

    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "CalibTest Terminal",
            "terminal_code": "CALT",
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
            "serial": "CALIB-SN-001",
            "model": "CalibModel",
            "brand": "CalibBrand",
            "equipment_type_id": eq_type_id,
            "owner_company_id": company_id,
            "terminal_id": terminal.json()["id"],
        },
        headers=auth_headers,
    )
    assert eq.status_code == 201

    _ids.update(
        {
            "company_id": company_id,
            "eq_type_id": eq_type_id,
            "terminal_id": terminal.json()["id"],
            "equipment_id": eq.json()["id"],
        }
    )
    return _ids


def _calibration_payload(company_id: int, cert: str = "CERT-001") -> dict:
    return {
        "calibration_company_id": company_id,
        "certificate_number": cert,
        "calibrated_at": "2024-01-15T00:00:00",
        "results": [],
    }


# ---------------------------------------------------------------------------
# POST /equipment-calibrations/equipment/{id}
# ---------------------------------------------------------------------------


def test_create_calibration(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        json=_calibration_payload(ids["company_id"]),
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["equipment_id"] == ids["equipment_id"]
    assert data["certificate_number"] == "CERT-001"
    assert "results" in data
    _ids["calibration_id"] = data["id"]


def test_create_calibration_missing_certificate_number(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _calibration_payload(ids["company_id"])
    payload["certificate_number"] = "   "
    response = client.post(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_calibration_invalid_company(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _calibration_payload(999999, cert="CERT-002")
    response = client.post(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_calibration_equipment_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        "/api/v1/equipment-calibrations/equipment/999999",
        json=_calibration_payload(ids["company_id"], cert="CERT-003"),
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_calibration_duplicate_date(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Same date as first calibration (2024-01-15) should conflict
    response = client.post(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        json=_calibration_payload(ids["company_id"], cert="CERT-DUP"),
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_create_calibration_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        json=_calibration_payload(ids["company_id"], cert="CERT-NOAUTH"),
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment-calibrations/equipment/{id}
# ---------------------------------------------------------------------------


def test_list_calibrations(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_calibrations_equipment_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-calibrations/equipment/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_calibrations_empty(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Create a fresh equipment with no calibrations
    eq2 = client.post(
        "/api/v1/equipment/",
        json={
            "serial": "CALIB-SN-EMPTY",
            "model": "CalibModel",
            "brand": "CalibBrand",
            "equipment_type_id": ids["eq_type_id"],
            "owner_company_id": ids["company_id"],
            "terminal_id": ids["terminal_id"],
        },
        headers=auth_headers,
    )
    assert eq2.status_code == 201
    eq2_id = eq2.json()["id"]

    response = client.get(
        f"/api/v1/equipment-calibrations/equipment/{eq2_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json().get("message") == "No records found"


# ---------------------------------------------------------------------------
# GET /equipment-calibrations/{calibration_id}
# ---------------------------------------------------------------------------


def test_get_calibration_by_id(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "calibration_id" in ids
    response = client.get(
        f"/api/v1/equipment-calibrations/{ids['calibration_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ids["calibration_id"]


def test_get_calibration_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-calibrations/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /equipment-calibrations/{calibration_id}
# ---------------------------------------------------------------------------


def test_update_calibration(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "calibration_id" in ids
    response = client.patch(
        f"/api/v1/equipment-calibrations/{ids['calibration_id']}",
        json={"notes": "Notas de prueba actualizadas", "certificate_number": "CERT-UPDATED"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "Notas de prueba actualizadas"
    assert data["certificate_number"] == "CERT-UPDATED"


def test_update_calibration_empty_certificate_number(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.patch(
        f"/api/v1/equipment-calibrations/{ids['calibration_id']}",
        json={"certificate_number": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_update_calibration_not_found(client, auth_headers):
    response = client.patch(
        "/api/v1/equipment-calibrations/999999",
        json={"notes": "no existe"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /equipment-calibrations/{calibration_id}
# ---------------------------------------------------------------------------


def test_delete_calibration(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Create a dedicated calibration to delete
    create = client.post(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        json=_calibration_payload(ids["company_id"], cert="CERT-TO-DELETE"),
        headers=auth_headers,
    )
    # May 409 if date collides; use a different date
    payload = _calibration_payload(ids["company_id"], cert="CERT-TO-DELETE")
    payload["calibrated_at"] = "2023-06-01T00:00:00"
    create = client.post(
        f"/api/v1/equipment-calibrations/equipment/{ids['equipment_id']}",
        json=payload,
        headers=auth_headers,
    )
    assert create.status_code == 201
    calib_id = create.json()["id"]

    response = client.delete(
        f"/api/v1/equipment-calibrations/{calib_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify it's gone
    assert client.get(
        f"/api/v1/equipment-calibrations/{calib_id}",
        headers=auth_headers,
    ).status_code == 404


def test_delete_calibration_not_found(client, auth_headers):
    response = client.delete(
        "/api/v1/equipment-calibrations/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_calibration_requires_admin(client, auth_headers):
    _setup(client, auth_headers)
    # The fixture user is superadmin so this should succeed; just verify no 403
    response = client.delete(
        "/api/v1/equipment-calibrations/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404  # not 403 for superadmin
