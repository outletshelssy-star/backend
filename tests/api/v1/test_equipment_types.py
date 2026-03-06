def _login_headers(client, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _make_payload(name: str, role: str = "reference") -> dict:
    """Payload mínimo válido: tipo de temperatura con error máximo en °C."""
    return {
        "name": name,
        "role": role,
        "calibration_days": 180,
        "maintenance_days": 90,
        "inspection_days": 30,
        "measures": ["temperature"],
        "max_errors": [{"measure": "temperature", "max_error_value": 0.5, "unit": "C"}],
    }


def _create_equipment_type(
    client, auth_headers, name: str, role: str = "reference"
) -> int:
    response = client.post(
        "/api/v1/equipment-types/",
        json=_make_payload(name, role),
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


# ---------------------------------------------------------------------------
# POST /equipment-types/
# ---------------------------------------------------------------------------


def test_create_equipment_type(client, auth_headers):
    response = client.post(
        "/api/v1/equipment-types/",
        json=_make_payload("Termometro Ref"),
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Termometro Ref"
    assert data["role"] == "reference"
    assert data["calibration_days"] == 180
    assert data["is_active"] is True
    assert data["created_by_user_id"] > 0
    assert data["measures"] == ["temperature"]
    assert len(data["max_errors"]) == 1
    assert data["max_errors"][0]["measure"] == "temperature"


def test_create_equipment_type_name_too_short(client, auth_headers):
    payload = _make_payload("X")
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 422


def test_create_equipment_type_invalid_role(client, auth_headers):
    payload = _make_payload("Tipo Invalid")
    payload["role"] = "invalid_role"
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 422


def test_create_equipment_type_negative_days(client, auth_headers):
    payload = _make_payload("Tipo Neg Days")
    payload["calibration_days"] = -1
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 422


def test_create_equipment_type_duplicate_measures(client, auth_headers):
    payload = {
        **_make_payload("Tipo Dup Measures"),
        "measures": ["temperature", "temperature"],
        "max_errors": [{"measure": "temperature", "max_error_value": 0.5, "unit": "C"}],
    }
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 400


def test_create_equipment_type_measures_max_errors_mismatch(client, auth_headers):
    payload = {
        **_make_payload("Tipo Mismatch"),
        "measures": ["temperature"],
        "max_errors": [{"measure": "weight", "max_error_value": 1.0, "unit": "g"}],
    }
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 400


def test_create_equipment_type_duplicate_max_errors(client, auth_headers):
    payload = {
        **_make_payload("Tipo Dup MaxErr"),
        "measures": ["temperature"],
        "max_errors": [
            {"measure": "temperature", "max_error_value": 0.5, "unit": "C"},
            {"measure": "temperature", "max_error_value": 1.0, "unit": "C"},
        ],
    }
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 400


def test_create_equipment_type_unit_normalization_temperature(client, auth_headers):
    # 68°F = 20°C
    payload = {
        **_make_payload("Tipo Temp F"),
        "measures": ["temperature"],
        "max_errors": [
            {"measure": "temperature", "max_error_value": 68.0, "unit": "F"}
        ],
    }
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 201
    stored = response.json()["max_errors"][0]["max_error_value"]
    assert abs(stored - 20.0) < 0.01  # 68°F ≈ 20°C


def test_create_equipment_type_unit_normalization_weight(client, auth_headers):
    # 1 kg = 1000 g
    payload = {
        **_make_payload("Tipo Weight Kg"),
        "measures": ["weight"],
        "max_errors": [{"measure": "weight", "max_error_value": 1.0, "unit": "kg"}],
    }
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 201
    stored = response.json()["max_errors"][0]["max_error_value"]
    assert stored == 1000.0


def test_create_equipment_type_unit_normalization_length(client, auth_headers):
    # 1 cm = 10 mm
    payload = {
        **_make_payload("Tipo Length Cm"),
        "measures": ["length"],
        "max_errors": [{"measure": "length", "max_error_value": 1.0, "unit": "cm"}],
    }
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 201
    stored = response.json()["max_errors"][0]["max_error_value"]
    assert stored == 10.0


def test_create_equipment_type_unsupported_unit(client, auth_headers):
    payload = {
        **_make_payload("Tipo Bad Unit"),
        "measures": ["temperature"],
        "max_errors": [
            {"measure": "temperature", "max_error_value": 1.0, "unit": "xyz"}
        ],
    }
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 400


def test_create_equipment_type_duplicate_name_role(client, auth_headers):
    payload = _make_payload("Tipo Duplicado")
    client.post("/api/v1/equipment-types/", json=payload, headers=auth_headers)

    # Mismo nombre y rol → debe retornar 409
    response = client.post(
        "/api/v1/equipment-types/", json=payload, headers=auth_headers
    )

    assert response.status_code == 409


def test_create_equipment_type_same_name_different_role(client, auth_headers):
    # La restricción única es (name, role); distinto rol debe ser aceptado
    client.post(
        "/api/v1/equipment-types/",
        json=_make_payload("Tipo Dual", role="reference"),
        headers=auth_headers,
    )
    response = client.post(
        "/api/v1/equipment-types/",
        json=_make_payload("Tipo Dual", role="working"),
        headers=auth_headers,
    )

    assert response.status_code == 201


def test_create_equipment_type_requires_auth(client, auth_headers):
    response = client.post("/api/v1/equipment-types/", json=_make_payload("Tipo Auth"))

    assert response.status_code == 401


def test_non_admin_cannot_create_equipment_type(client, auth_headers):
    me = client.get("/api/v1/users/me", headers=auth_headers)
    company_id = me.json()["company_id"]

    client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "EqType",
            "email": "normaleqtype@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    normal_headers = _login_headers(client, "normaleqtype@test.com", "supersecret123")

    response = client.post(
        "/api/v1/equipment-types/",
        json=_make_payload("Tipo Normal"),
        headers=normal_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /equipment-types/
# ---------------------------------------------------------------------------


def test_list_equipment_types(client, auth_headers):
    _create_equipment_type(client, auth_headers, "Tipo List")

    response = client.get("/api/v1/equipment-types/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1
    # measures y max_errors siempre se incluyen
    item = data["items"][0]
    assert "measures" in item
    assert "max_errors" in item
    assert isinstance(item["measures"], list)
    assert isinstance(item["max_errors"], list)


def test_list_equipment_types_requires_auth(client):
    response = client.get("/api/v1/equipment-types/")

    assert response.status_code == 401


def test_list_equipment_types_with_include_creator(client, auth_headers):
    _create_equipment_type(client, auth_headers, "Tipo Include List")

    response = client.get(
        "/api/v1/equipment-types/?include=creator", headers=auth_headers
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    item_with_creator = next((i for i in items if i["creator"] is not None), None)
    assert item_with_creator is not None
    assert "id" in item_with_creator["creator"]


# ---------------------------------------------------------------------------
# GET /equipment-types/{id}
# ---------------------------------------------------------------------------


def test_get_equipment_type_by_id(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Get")

    response = client.get(f"/api/v1/equipment-types/{et_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == et_id
    assert data["name"] == "Tipo Get"
    assert isinstance(data["measures"], list)
    assert isinstance(data["max_errors"], list)


def test_get_equipment_type_not_found(client, auth_headers):
    response = client.get("/api/v1/equipment-types/99999", headers=auth_headers)

    assert response.status_code == 404


def test_get_equipment_type_requires_auth(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Get Auth")

    response = client.get(f"/api/v1/equipment-types/{et_id}")

    assert response.status_code == 401


def test_get_equipment_type_with_include_creator(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Include Get")

    # Sin include: creator es None
    plain = client.get(f"/api/v1/equipment-types/{et_id}", headers=auth_headers)
    assert plain.status_code == 200
    assert plain.json()["creator"] is None

    # Con include=creator: creator está poblado
    with_include = client.get(
        f"/api/v1/equipment-types/{et_id}?include=creator", headers=auth_headers
    )
    assert with_include.status_code == 200
    assert with_include.json()["creator"] is not None


# ---------------------------------------------------------------------------
# PUT /equipment-types/{id}
# ---------------------------------------------------------------------------


def test_update_equipment_type(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Update")

    response = client.put(
        f"/api/v1/equipment-types/{et_id}",
        json={"name": "Tipo Actualizado", "is_active": False},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Tipo Actualizado"
    assert data["is_active"] is False


def test_update_equipment_type_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/equipment-types/99999",
        json={"name": "No Existe"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_equipment_type_name_too_short(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Short Name")

    response = client.put(
        f"/api/v1/equipment-types/{et_id}",
        json={"name": "X"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_equipment_type_measures_without_max_errors(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo No MaxErr")

    # measures sin max_errors → 400
    response = client.put(
        f"/api/v1/equipment-types/{et_id}",
        json={"measures": ["weight"]},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_update_equipment_type_max_errors_without_measures(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo No Measures")

    # max_errors sin measures → 400
    response = client.put(
        f"/api/v1/equipment-types/{et_id}",
        json={
            "max_errors": [{"measure": "weight", "max_error_value": 1.0, "unit": "g"}]
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_update_equipment_type_measures_and_max_errors(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Both Update")

    # Reemplazar temperature por weight
    response = client.put(
        f"/api/v1/equipment-types/{et_id}",
        json={
            "measures": ["weight"],
            "max_errors": [
                {"measure": "weight", "max_error_value": 500.0, "unit": "g"}
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["measures"] == ["weight"]
    assert data["max_errors"][0]["measure"] == "weight"
    assert data["max_errors"][0]["max_error_value"] == 500.0


def test_update_equipment_type_role_change(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Role Change")

    response = client.put(
        f"/api/v1/equipment-types/{et_id}",
        json={"role": "working"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["role"] == "working"


def test_update_equipment_type_requires_auth(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Auth Put")

    response = client.put(f"/api/v1/equipment-types/{et_id}", json={"name": "Sin Auth"})

    assert response.status_code == 401


def test_non_admin_cannot_update_equipment_type(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Protect Put")

    me = client.get("/api/v1/users/me", headers=auth_headers)
    company_id = me.json()["company_id"]
    client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "EqUpd",
            "email": "normalequpd@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    normal_headers = _login_headers(client, "normalequpd@test.com", "supersecret123")

    response = client.put(
        f"/api/v1/equipment-types/{et_id}",
        json={"name": "Hackeado"},
        headers=normal_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /equipment-types/{id}
# ---------------------------------------------------------------------------


def test_delete_equipment_type(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Delete")

    delete_response = client.delete(
        f"/api/v1/equipment-types/{et_id}", headers=auth_headers
    )

    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["action"] == "deleted"
    assert payload["equipment_type"]["id"] == et_id

    get_response = client.get(f"/api/v1/equipment-types/{et_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_delete_equipment_type_not_found(client, auth_headers):
    response = client.delete("/api/v1/equipment-types/99999", headers=auth_headers)

    assert response.status_code == 404


def test_delete_equipment_type_requires_auth(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Auth Del")

    response = client.delete(f"/api/v1/equipment-types/{et_id}")

    assert response.status_code == 401


def test_non_admin_cannot_delete_equipment_type(client, auth_headers):
    et_id = _create_equipment_type(client, auth_headers, "Tipo Protect Del")

    me = client.get("/api/v1/users/me", headers=auth_headers)
    company_id = me.json()["company_id"]
    client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "EqDel",
            "email": "normaleqdel@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    normal_headers = _login_headers(client, "normaleqdel@test.com", "supersecret123")

    response = client.delete(f"/api/v1/equipment-types/{et_id}", headers=normal_headers)

    assert response.status_code == 403
