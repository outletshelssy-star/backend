# Module-level IDs cache — populated once per test session (lazy setup)
_ids: dict = {}


def _login_headers(
    client, email: str = "admin@local.dev", password: str = "supersecret123"
) -> dict:
    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _setup(client, auth_headers) -> dict:
    """Lazy-create shared prerequisites (equipment type, block, terminal) once."""
    if _ids:
        return _ids

    me = client.get("/api/v1/users/me", headers=auth_headers).json()
    company_id = me["company_id"]

    # Equipment type 1
    et1 = client.post(
        "/api/v1/equipment-types/",
        json={
            "name": "EQTest Thermometer",
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
    assert et1.status_code == 201
    eq_type_id = et1.json()["id"]

    # Equipment type 2 (for type-change tests)
    et2 = client.post(
        "/api/v1/equipment-types/",
        json={
            "name": "EQTest Barometer",
            "role": "working",
            "calibration_days": 180,
            "maintenance_days": 90,
            "inspection_days": 30,
            "measures": ["temperature"],
            "max_errors": [
                {"measure": "temperature", "max_error_value": 1.0, "unit": "C"}
            ],
        },
        headers=auth_headers,
    )
    assert et2.status_code == 201
    eq_type_id2 = et2.json()["id"]

    # Block
    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "EQTest Block", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert block.status_code == 201
    block_id = block.json()["id"]

    # Admin company (client company for terminal)
    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "EQTest Admin Company", "company_type": "client"},
        headers=auth_headers,
    )
    assert admin_co.status_code == 201
    admin_company_id = admin_co.json()["id"]

    # Terminal
    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "EQTest Terminal",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "EQTX",
        },
        headers=auth_headers,
    )
    assert terminal.status_code == 201
    terminal_id = terminal.json()["id"]

    _ids.update(
        {
            "company_id": company_id,
            "eq_type_id": eq_type_id,
            "eq_type_id2": eq_type_id2,
            "terminal_id": terminal_id,
            "admin_company_id": admin_company_id,
            "block_id": block_id,
        }
    )
    return _ids


def _make_payload(ids: dict, *, serial: str = "SN-EQTEST") -> dict:
    """Minimal valid equipment payload."""
    return {
        "serial": serial,
        "model": "TestModel",
        "brand": "TestBrand",
        "equipment_type_id": ids["eq_type_id"],
        "owner_company_id": ids["company_id"],
        "terminal_id": ids["terminal_id"],
    }


def _create_equipment(
    client, auth_headers, ids: dict, *, serial: str = "SN-EQTEST-AUTO"
) -> int:
    r = client.post(
        "/api/v1/equipment/",
        json=_make_payload(ids, serial=serial),
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# POST /equipment/
# ---------------------------------------------------------------------------


def test_create_equipment(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post(
        "/api/v1/equipment/",
        json=_make_payload(ids, serial="SN-CREATE-001"),
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["serial"] == "SN-CREATE-001"
    assert data["model"] == "TestModel"
    assert data["brand"] == "TestBrand"
    assert data["equipment_type_id"] == ids["eq_type_id"]
    assert data["owner_company_id"] == ids["company_id"]
    assert data["terminal_id"] == ids["terminal_id"]
    assert data["is_active"] is True
    assert isinstance(data["component_serials"], list)
    assert isinstance(data["measure_specs"], list)


def test_create_equipment_with_component_serials(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-COMP-001")
    payload["component_serials"] = [
        {"component_name": "Sensor", "serial": "SENS-001"},
        {"component_name": "Display", "serial": "DISP-001"},
    ]

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert len(data["component_serials"]) == 2
    names = {c["component_name"] for c in data["component_serials"]}
    assert names == {"Sensor", "Display"}


def test_create_equipment_with_measure_specs(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-SPEC-001")
    payload["measure_specs"] = [
        {
            "measure": "temperature",
            "min_unit": "C",
            "max_unit": "C",
            "resolution_unit": "C",
            "min_value": -20.0,
            "max_value": 100.0,
            "resolution": 0.1,
        }
    ]

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert len(data["measure_specs"]) == 1
    spec = data["measure_specs"][0]
    assert spec["measure"] == "temperature"
    assert spec["min_value"] == -20.0
    assert spec["max_value"] == 100.0


def test_create_equipment_invalid_equipment_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-BADTYPE")
    payload["equipment_type_id"] = 999999

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 404


def test_create_equipment_invalid_company(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-BADCO")
    payload["owner_company_id"] = 999999

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 404


def test_create_equipment_invalid_terminal(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-BADTERM")
    payload["terminal_id"] = 999999

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 404


def test_create_equipment_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        "/api/v1/equipment/",
        json=_make_payload(ids, serial="SN-NOAUTH"),
    )

    assert response.status_code == 401


def test_create_equipment_non_admin_forbidden(client, auth_headers):
    ids = _setup(client, auth_headers)

    client.post(
        "/api/v1/users/",
        json={
            "name": "Visitor",
            "last_name": "EQ",
            "email": "visitor.eq@test.com",
            "password": "supersecret123",
            "is_active": True,
            "user_type": "visitor",
            "company_id": ids["company_id"],
        },
        headers=auth_headers,
    )
    visitor_headers = _login_headers(client, "visitor.eq@test.com")

    response = client.post(
        "/api/v1/equipment/",
        json=_make_payload(ids, serial="SN-VISITOR"),
        headers=visitor_headers,
    )

    assert response.status_code == 403


def test_create_equipment_weight_fields_incomplete(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-WCLASS-BAD")
    payload["weight_class"] = "F1"
    # nominal_mass_value and nominal_mass_unit missing → 400

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 400


def test_create_equipment_weight_serial_invalid(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Serial must end with "100G" for a 100g weight; "WRONG-SERIAL" does not
    payload = _make_payload(ids, serial="WRONG-SERIAL")
    payload["weight_class"] = "F1"
    payload["nominal_mass_value"] = 100.0
    payload["nominal_mass_unit"] = "g"

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 400


def test_create_equipment_measure_min_greater_than_max(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-MINMAX")
    payload["measure_specs"] = [
        {
            "measure": "temperature",
            "min_unit": "C",
            "max_unit": "C",
            "resolution_unit": "C",
            "min_value": 100.0,
            "max_value": -20.0,
        }
    ]

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 400


def test_create_equipment_measure_invalid_resolution(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _make_payload(ids, serial="SN-RES-ZERO")
    payload["measure_specs"] = [
        {
            "measure": "temperature",
            "min_unit": "C",
            "max_unit": "C",
            "resolution_unit": "C",
            "min_value": 0.0,
            "max_value": 100.0,
            "resolution": 0.0,
        }
    ]

    response = client.post("/api/v1/equipment/", json=payload, headers=auth_headers)

    assert response.status_code == 400


def test_create_equipment_creates_type_and_terminal_history(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-HIST-CREATE")

    type_hist = client.get(
        f"/api/v1/equipment/{eq_id}/type-history", headers=auth_headers
    )
    term_hist = client.get(
        f"/api/v1/equipment/{eq_id}/terminal-history", headers=auth_headers
    )

    assert type_hist.status_code == 200
    assert len(type_hist.json()["items"]) >= 1
    assert type_hist.json()["items"][0]["equipment_type_id"] == ids["eq_type_id"]

    assert term_hist.status_code == 200
    assert len(term_hist.json()["items"]) >= 1


# ---------------------------------------------------------------------------
# GET /equipment/
# ---------------------------------------------------------------------------


def test_list_equipment(client, auth_headers):
    ids = _setup(client, auth_headers)
    _create_equipment(client, auth_headers, ids, serial="SN-LIST-001")

    response = client.get("/api/v1/equipment/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_equipment_requires_auth(client):
    response = client.get("/api/v1/equipment/")

    assert response.status_code == 401


def test_list_equipment_include_equipment_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    _create_equipment(client, auth_headers, ids, serial="SN-LIST-INC-001")

    response = client.get(
        "/api/v1/equipment/?include=equipment_type", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    items_with_type = [i for i in data["items"] if i.get("equipment_type") is not None]
    assert len(items_with_type) >= 1


def test_list_equipment_include_creator(client, auth_headers):
    ids = _setup(client, auth_headers)
    _create_equipment(client, auth_headers, ids, serial="SN-LIST-CR-001")

    response = client.get("/api/v1/equipment/?include=creator", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    items_with_creator = [i for i in data["items"] if i.get("creator") is not None]
    assert len(items_with_creator) >= 1


def test_list_equipment_include_owner_company(client, auth_headers):
    ids = _setup(client, auth_headers)
    _create_equipment(client, auth_headers, ids, serial="SN-LIST-OC-001")

    response = client.get(
        "/api/v1/equipment/?include=owner_company", headers=auth_headers
    )

    assert response.status_code == 200
    items_with_company = [
        i for i in response.json()["items"] if i.get("owner_company") is not None
    ]
    assert len(items_with_company) >= 1


# ---------------------------------------------------------------------------
# GET /equipment/{id}
# ---------------------------------------------------------------------------


def test_get_equipment(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-GET-001")

    response = client.get(f"/api/v1/equipment/{eq_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == eq_id
    assert data["serial"] == "SN-GET-001"


def test_get_equipment_not_found(client, auth_headers):
    response = client.get("/api/v1/equipment/999999", headers=auth_headers)

    assert response.status_code == 404


def test_get_equipment_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-GET-NOAUTH")

    response = client.get(f"/api/v1/equipment/{eq_id}")

    assert response.status_code == 401


def test_get_equipment_include_owner_company(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-GET-OC-001")

    response = client.get(
        f"/api/v1/equipment/{eq_id}?include=owner_company", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["owner_company"] is not None
    assert data["owner_company"]["id"] == ids["company_id"]


def test_get_equipment_include_terminal(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-GET-TERM-001")

    response = client.get(
        f"/api/v1/equipment/{eq_id}?include=terminal", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["terminal"] is not None
    assert data["terminal"]["id"] == ids["terminal_id"]


def test_get_equipment_include_equipment_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-GET-ET-001")

    response = client.get(
        f"/api/v1/equipment/{eq_id}?include=equipment_type", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["equipment_type"] is not None
    assert data["equipment_type"]["id"] == ids["eq_type_id"]


# ---------------------------------------------------------------------------
# PATCH /equipment/{id}
# ---------------------------------------------------------------------------


def test_update_equipment(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-UPD-001")

    response = client.patch(
        f"/api/v1/equipment/{eq_id}",
        json={"brand": "UpdatedBrand"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["brand"] == "UpdatedBrand"


def test_update_equipment_not_found(client, auth_headers):
    response = client.patch(
        "/api/v1/equipment/999999",
        json={"brand": "X"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_equipment_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-UPD-NOAUTH")

    response = client.patch(f"/api/v1/equipment/{eq_id}", json={"brand": "X"})

    assert response.status_code == 401


def test_update_equipment_type_change_creates_history(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-TYPECHG-001")

    client.patch(
        f"/api/v1/equipment/{eq_id}",
        json={"equipment_type_id": ids["eq_type_id2"]},
        headers=auth_headers,
    )

    history_resp = client.get(
        f"/api/v1/equipment/{eq_id}/type-history", headers=auth_headers
    )

    assert history_resp.status_code == 200
    items = history_resp.json()["items"]
    # Initial entry + new entry after type change
    assert len(items) >= 2


def test_update_equipment_invalid_equipment_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-UPD-BADTYPE")

    response = client.patch(
        f"/api/v1/equipment/{eq_id}",
        json={"equipment_type_id": 999999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_equipment_invalid_terminal(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-UPD-BADTERM")

    response = client.patch(
        f"/api/v1/equipment/{eq_id}",
        json={"terminal_id": 999999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_equipment_measure_specs(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-UPD-SPEC-001")

    response = client.patch(
        f"/api/v1/equipment/{eq_id}",
        json={
            "measure_specs": [
                {
                    "measure": "temperature",
                    "min_unit": "C",
                    "max_unit": "C",
                    "resolution_unit": "C",
                    "min_value": 0.0,
                    "max_value": 50.0,
                }
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["measure_specs"]) == 1
    assert data["measure_specs"][0]["max_value"] == 50.0


def test_update_equipment_component_serials(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-UPD-COMP-001")

    response = client.patch(
        f"/api/v1/equipment/{eq_id}",
        json={
            "component_serials": [{"component_name": "Battery", "serial": "BAT-001"}]
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["component_serials"]) == 1
    assert data["component_serials"][0]["component_name"] == "Battery"


def test_update_equipment_status(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-UPD-STATUS")

    response = client.patch(
        f"/api/v1/equipment/{eq_id}",
        json={"status": "maintenance"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "maintenance"


# ---------------------------------------------------------------------------
# DELETE /equipment/{id}
# ---------------------------------------------------------------------------


def test_delete_equipment_no_activity(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-DEL-001")

    response = client.delete(f"/api/v1/equipment/{eq_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "deleted"
    assert data["equipment"]["id"] == eq_id


def test_delete_equipment_verifies_gone(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-DEL-GONE")

    client.delete(f"/api/v1/equipment/{eq_id}", headers=auth_headers)
    response = client.get(f"/api/v1/equipment/{eq_id}", headers=auth_headers)

    assert response.status_code == 404


def test_delete_equipment_not_found(client, auth_headers):
    response = client.delete("/api/v1/equipment/999999", headers=auth_headers)

    assert response.status_code == 404


def test_delete_equipment_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-DEL-NOAUTH")

    response = client.delete(f"/api/v1/equipment/{eq_id}")

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment/{id}/type-history
# ---------------------------------------------------------------------------


def test_get_type_history(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-TH-001")

    response = client.get(
        f"/api/v1/equipment/{eq_id}/type-history", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["equipment_type_id"] == ids["eq_type_id"]


def test_get_type_history_not_found(client, auth_headers):
    response = client.get("/api/v1/equipment/999999/type-history", headers=auth_headers)

    assert response.status_code == 404


def test_get_type_history_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-TH-NOAUTH")

    response = client.get(f"/api/v1/equipment/{eq_id}/type-history")

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment/{id}/terminal-history
# ---------------------------------------------------------------------------


def test_get_terminal_history(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-TERMH-001")

    response = client.get(
        f"/api/v1/equipment/{eq_id}/terminal-history", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_get_terminal_history_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/equipment/999999/terminal-history", headers=auth_headers
    )

    assert response.status_code == 404


def test_get_terminal_history_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-TERMH-NOAUTH")

    response = client.get(f"/api/v1/equipment/{eq_id}/terminal-history")

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /equipment/{id}/history
# ---------------------------------------------------------------------------


def test_get_history(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-HIST-FULL")

    response = client.get(f"/api/v1/equipment/{eq_id}/history", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    # On creation: 1 type-history entry + 1 terminal-history entry
    assert len(data["items"]) >= 2


def test_get_history_not_found(client, auth_headers):
    response = client.get("/api/v1/equipment/999999/history", headers=auth_headers)

    assert response.status_code == 404


def test_get_history_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    eq_id = _create_equipment(client, auth_headers, ids, serial="SN-HIST-NOAUTH")

    response = client.get(f"/api/v1/equipment/{eq_id}/history")

    assert response.status_code == 401
