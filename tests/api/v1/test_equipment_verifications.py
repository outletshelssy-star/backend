"""
Tests for equipment verifications.

Uses a generic equipment type (not matching any special-case name like
"termometro", "cinta", "balanza", "hidrometro", "titulador karl fischer")
so that the comparison / special-logic rules are skipped.

Setup requires:
  - Equipment type with calibration_days=0
  - One active verification type with no required items
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
            "name": "VerifTest Presurometro",
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

    # Verification type
    vt = client.post(
        f"/api/v1/equipment-type-verifications/equipment-type/{eq_type_id}",
        json={"name": "Verificacion Diaria", "frequency_days": 1, "is_active": True},
        headers=auth_headers,
    )
    assert vt.status_code == 201
    verification_type_id = vt.json()["id"]

    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "VerifTest Block", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert block.status_code == 201

    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "VerifTest Admin Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert admin_co.status_code == 201

    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "VerifTest Terminal",
            "terminal_code": "VFTS",
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
            "serial": "VERIF-SN-001",
            "model": "VerifModel",
            "brand": "VerifBrand",
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
            "certificate_number": "VERIF-CERT-001",
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
            "verification_type_id": verification_type_id,
            "terminal_id": terminal.json()["id"],
            "equipment_id": equipment_id,
        }
    )
    return _ids


def _verification_payload(ids: dict, date: str = "2024-03-01T08:00:00") -> dict:
    return {
        "verification_type_id": ids["verification_type_id"],
        "verified_at": date,
        "notes": "Verificacion OK",
        "responses": [],
    }


# ---------------------------------------------------------------------------
# POST /equipment-verifications/equipment/{id}
# ---------------------------------------------------------------------------


def test_create_verification(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-verifications/equipment/{ids['equipment_id']}",
        json=_verification_payload(ids),
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["equipment_id"] == ids["equipment_id"]
    assert data["verification_type_id"] == ids["verification_type_id"]
    _ids["verification_id"] = data["id"]


def test_create_verification_equipment_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        "/api/v1/equipment-verifications/equipment/999999",
        json=_verification_payload(ids),
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_verification_invalid_verification_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _verification_payload(ids, date="2024-03-02T08:00:00")
    payload["verification_type_id"] = 999999
    response = client.post(
        f"/api/v1/equipment-verifications/equipment/{ids['equipment_id']}",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_verification_same_day_conflict(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Same date as test_create_verification (2024-03-01)
    response = client.post(
        f"/api/v1/equipment-verifications/equipment/{ids['equipment_id']}",
        json=_verification_payload(ids, date="2024-03-01T10:00:00"),
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_create_verification_replace_existing(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-verifications/equipment/{ids['equipment_id']}?replace_existing=true",
        json=_verification_payload(ids, date="2024-03-01T12:00:00"),
        headers=auth_headers,
    )
    assert response.status_code == 201
    _ids["verification_id"] = response.json()["id"]


def test_create_verification_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        f"/api/v1/equipment-verifications/equipment/{ids['equipment_id']}",
        json=_verification_payload(ids, date="2024-05-01T08:00:00"),
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment-verifications/equipment/{id}
# ---------------------------------------------------------------------------


def test_list_verifications(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/equipment-verifications/equipment/{ids['equipment_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_verifications_equipment_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-verifications/equipment/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /equipment-verifications/{verification_id}
# ---------------------------------------------------------------------------


def test_get_verification_by_id(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "verification_id" in ids
    response = client.get(
        f"/api/v1/equipment-verifications/{ids['verification_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ids["verification_id"]


def test_get_verification_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment-verifications/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /equipment-verifications/{verification_id}
# ---------------------------------------------------------------------------


def test_update_verification(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "verification_id" in ids
    response = client.patch(
        f"/api/v1/equipment-verifications/{ids['verification_id']}",
        json={"notes": "Notas actualizadas", "responses": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Notas actualizadas"


def test_update_verification_not_found(client, auth_headers):
    response = client.patch(
        "/api/v1/equipment-verifications/999999",
        json={"notes": "no existe", "responses": []},
        headers=auth_headers,
    )
    assert response.status_code == 404
