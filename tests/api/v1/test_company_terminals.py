def _login_headers(client, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_company_id(client, auth_headers) -> int:
    response = client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert response.status_code == 200
    company_id = response.json()["company_id"]
    assert company_id is not None
    return company_id


def _create_block(client, auth_headers, company_id: int) -> int:
    response = client.post(
        "/api/v1/company-blocks/",
        json={
            "name": "Terminal Block",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_admin_company(client, auth_headers) -> int:
    response = client.post(
        "/api/v1/companies/",
        json={
            "name": "Admin Co",
            "company_type": "client",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_company_terminal(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal A",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "TA01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Terminal A"
    assert data["is_active"] is True
    assert data["block_id"] == block_id
    assert data["owner_company_id"] == owner_company_id
    assert data["admin_company_id"] == admin_company_id
    assert data["created_by_user_id"] > 0


def test_list_company_terminals(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal List",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "TL01",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/company-terminals/",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


def test_get_company_terminal_by_id(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal B",
            "is_active": False,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "TB01",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    terminal_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/company-terminals/{terminal_id}?owner_company_id={owner_company_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Terminal B"


def test_company_terminals_requires_auth(client):
    response = client.get("/api/v1/company-terminals/")

    assert response.status_code == 401


def test_non_admin_cannot_access_company_terminals(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_user_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "User",
            "email": "terminaluser@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_user_response.status_code == 201

    normal_headers = _login_headers(client, "terminaluser@test.com", "supersecret123")

    # GET /company-terminals/ is open to all authenticated users
    list_response = client.get(
        "/api/v1/company-terminals/",
        headers=normal_headers,
    )
    assert list_response.status_code == 200

    # POST /company-terminals/ requires admin or superadmin
    create_response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Nope Terminal",
            "is_active": True,
            "has_lab": True,
            "block_id": 1,
            "owner_company_id": company_id,
            "admin_company_id": company_id,
            "terminal_code": "NT01",
        },
        headers=normal_headers,
    )
    assert create_response.status_code == 403


def test_get_company_terminal_not_found(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    response = client.get(
        f"/api/v1/company-terminals/99999?owner_company_id={owner_company_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_company_terminal_invalid_admin_company(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Invalid Admin",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": 99999,
            "terminal_code": "TIA1",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_company_terminal_invalid_block(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    admin_company_id = _create_admin_company(client, auth_headers)
    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Invalid Block",
            "is_active": True,
            "has_lab": True,
            "block_id": 99999,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "TIB1",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------


def _create_terminal(
    client,
    auth_headers,
    *,
    owner_company_id: int,
    block_id: int,
    admin_company_id: int,
    name: str = "Terminal Help",
    code: str = "TH01",
    has_lab: bool = True,
    lab_terminal_id: int | None = None,
) -> int:
    payload = {
        "name": name,
        "is_active": True,
        "has_lab": has_lab,
        "block_id": block_id,
        "owner_company_id": owner_company_id,
        "admin_company_id": admin_company_id,
        "terminal_code": code,
    }
    if lab_terminal_id is not None:
        payload["lab_terminal_id"] = lab_terminal_id
    response = client.post(
        "/api/v1/company-terminals/", json=payload, headers=auth_headers
    )
    assert response.status_code == 201
    return response.json()["id"]


# ---------------------------------------------------------------------------
# POST /company-terminals/ — validaciones adicionales
# ---------------------------------------------------------------------------


def test_create_company_terminal_name_too_short(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "X",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "TC01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_company_terminal_invalid_owner_company(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Sin Owner",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": 99999,
            "admin_company_id": admin_company_id,
            "terminal_code": "TO01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_company_terminal_name_is_normalized(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "terminal norte",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "TN01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Terminal Norte"


def test_create_company_terminal_code_too_short(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Code Short",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "TC",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_company_terminal_code_invalid_chars(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Code Inv",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "T@01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_company_terminal_code_is_uppercased(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Code Up",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "tu01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["terminal_code"] == "TU01"


def test_create_company_terminal_has_lab_with_lab_terminal_id(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    lab_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        name="Lab Terminal",
        code="LT01",
    )

    # has_lab=True no debe llevar lab_terminal_id
    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Has Lab",
            "is_active": True,
            "has_lab": True,
            "lab_terminal_id": lab_id,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "HL01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_create_company_terminal_no_lab_without_lab_terminal_id(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    # has_lab=False requiere lab_terminal_id
    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal No Lab",
            "is_active": True,
            "has_lab": False,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "NL01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_create_company_terminal_block_wrong_company(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    other_company_id = _create_admin_company(client, auth_headers)
    block_other = _create_block(client, auth_headers, other_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    # block pertenece a other_company, no al owner_company
    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Block Co",
            "is_active": True,
            "has_lab": True,
            "block_id": block_other,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "BW01",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_company_terminal_requires_auth(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    response = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "Terminal Auth",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": owner_company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "AU01",
        },
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /company-terminals/ — filtros e include
# ---------------------------------------------------------------------------


def test_list_company_terminals_filter_owner_company_id(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    other_company_id = _create_admin_company(client, auth_headers)
    block_owner = _create_block(client, auth_headers, owner_company_id)
    block_other = _create_block(client, auth_headers, other_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_owner,
        admin_company_id=admin_company_id,
        name="Terminal Owner",
        code="FO01",
    )
    _create_terminal(
        client,
        auth_headers,
        owner_company_id=other_company_id,
        block_id=block_other,
        admin_company_id=admin_company_id,
        name="Terminal Other",
        code="FT01",
    )

    response = client.get(
        f"/api/v1/company-terminals/?owner_company_id={owner_company_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["owner_company_id"] == owner_company_id for item in items)


def test_list_company_terminals_with_include_creator(client, auth_headers):
    response = client.get(
        "/api/v1/company-terminals/?include=creator",
        headers=auth_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    terminal_with_creator = next((t for t in items if t["creator"] is not None), None)
    assert terminal_with_creator is not None
    assert "id" in terminal_with_creator["creator"]


def test_list_company_terminals_with_include_owner_company(client, auth_headers):
    response = client.get(
        "/api/v1/company-terminals/?include=owner_company",
        headers=auth_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    terminal_with_company = next(
        (t for t in items if t["owner_company"] is not None), None
    )
    assert terminal_with_company is not None
    assert "id" in terminal_with_company["owner_company"]
    assert "name" in terminal_with_company["owner_company"]


# ---------------------------------------------------------------------------
# GET /company-terminals/{id} — auth, include, owner_company_id requerido
# ---------------------------------------------------------------------------


def test_get_company_terminal_by_id_requires_auth(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="GA01",
    )

    response = client.get(
        f"/api/v1/company-terminals/{terminal_id}?owner_company_id={owner_company_id}"
    )

    assert response.status_code == 401


def test_get_company_terminal_wrong_owner_company_id(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="GW01",
    )

    response = client.get(
        f"/api/v1/company-terminals/{terminal_id}?owner_company_id=99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_get_company_terminal_missing_owner_company_id(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="GM01",
    )

    # owner_company_id es requerido; omitirlo debe retornar 422
    response = client.get(
        f"/api/v1/company-terminals/{terminal_id}",
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_get_company_terminal_with_include(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="GI01",
    )

    # Sin include: relaciones son None
    plain = client.get(
        f"/api/v1/company-terminals/{terminal_id}?owner_company_id={owner_company_id}",
        headers=auth_headers,
    )
    assert plain.status_code == 200
    assert plain.json()["owner_company"] is None
    assert plain.json()["creator"] is None

    # Con include=owner_company,creator: relaciones pobladas
    with_include = client.get(
        f"/api/v1/company-terminals/{terminal_id}"
        f"?owner_company_id={owner_company_id}&include=owner_company,creator",
        headers=auth_headers,
    )
    assert with_include.status_code == 200
    data = with_include.json()
    assert data["owner_company"] is not None
    assert data["creator"] is not None


# ---------------------------------------------------------------------------
# PUT /company-terminals/{id}
# ---------------------------------------------------------------------------


def test_update_company_terminal(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        name="Terminal Vieja",
        code="UV01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"name": "Terminal Nueva", "is_active": False},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Terminal Nueva"
    assert data["is_active"] is False


def test_update_company_terminal_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/company-terminals/99999",
        json={"name": "No Existe"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_company_terminal_name_too_short(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="US01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"name": "X"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_company_terminal_name_is_normalized(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="UN01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"name": "terminal actualizada"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Terminal Actualizada"


def test_update_company_terminal_code_is_uppercased(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="UC01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"terminal_code": "uc02"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["terminal_code"] == "UC02"


def test_update_company_terminal_invalid_owner_company(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="UO01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"owner_company_id": 99999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_company_terminal_invalid_block(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="UB01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"block_id": 99999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_company_terminal_invalid_admin_company(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="UA01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"admin_company_id": 99999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_company_terminal_lab_self_reference(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)

    # Terminal A con lab propio
    lab_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        name="Lab Terminal SR",
        code="SR01",
    )
    # Terminal B sin lab, apuntando a A
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        name="Terminal Sin Lab",
        code="SR02",
        has_lab=False,
        lab_terminal_id=lab_id,
    )

    # Intentar que B se apunte a sí mismo
    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"lab_terminal_id": terminal_id},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_update_company_terminal_requires_auth(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="UR01",
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"name": "Sin Auth"},
    )

    assert response.status_code == 401


def test_non_admin_cannot_update_company_terminal(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="UP01",
    )

    create_user = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "TermUpdater",
            "email": "normaltermupdater@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": owner_company_id,
        },
        headers=auth_headers,
    )
    assert create_user.status_code == 201

    normal_headers = _login_headers(
        client, "normaltermupdater@test.com", "supersecret123"
    )

    response = client.put(
        f"/api/v1/company-terminals/{terminal_id}",
        json={"name": "Hackeada"},
        headers=normal_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /company-terminals/{id}
# ---------------------------------------------------------------------------


def test_delete_company_terminal(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        name="Terminal Eliminar",
        code="DE01",
    )

    delete_response = client.delete(
        f"/api/v1/company-terminals/{terminal_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["action"] == "deleted"
    assert payload["terminal"]["id"] == terminal_id

    get_response = client.get(
        f"/api/v1/company-terminals/{terminal_id}?owner_company_id={owner_company_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


def test_delete_company_terminal_not_found(client, auth_headers):
    response = client.delete(
        "/api/v1/company-terminals/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_company_terminal_requires_auth(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="DR01",
    )

    response = client.delete(f"/api/v1/company-terminals/{terminal_id}")

    assert response.status_code == 401


def test_non_admin_cannot_delete_company_terminal(client, auth_headers):
    owner_company_id = _admin_company_id(client, auth_headers)
    block_id = _create_block(client, auth_headers, owner_company_id)
    admin_company_id = _create_admin_company(client, auth_headers)
    terminal_id = _create_terminal(
        client,
        auth_headers,
        owner_company_id=owner_company_id,
        block_id=block_id,
        admin_company_id=admin_company_id,
        code="DP01",
    )

    create_user = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "TermDeleter",
            "email": "normaltermdeleter@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": owner_company_id,
        },
        headers=auth_headers,
    )
    assert create_user.status_code == 201

    normal_headers = _login_headers(
        client, "normaltermdeleter@test.com", "supersecret123"
    )

    response = client.delete(
        f"/api/v1/company-terminals/{terminal_id}",
        headers=normal_headers,
    )

    assert response.status_code == 403
