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
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    company_id = response.json()["company_id"]
    assert company_id is not None
    return company_id


def test_create_company_block(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/company-blocks/",
        json={
            "name": "Bloque A",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Bloque A"
    assert data["is_active"] is True
    assert data["company_id"] == company_id
    assert data["created_by_user_id"] > 0


def test_list_company_blocks(client, auth_headers):
    response = client.get(
        "/api/v1/company-blocks/",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


def test_get_company_block_by_id(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={
            "name": "Bloque B",
            "is_active": False,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/company-blocks/{block_id}?company_id={company_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Bloque B"


def test_company_blocks_requires_auth(client):
    response = client.get("/api/v1/company-blocks/")

    assert response.status_code == 401


def test_non_admin_cannot_access_company_blocks(client, auth_headers):
    me_response = client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert me_response.status_code == 200
    company_id = me_response.json()["company_id"]
    assert company_id is not None

    create_user_response = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "User",
            "email": "blockuser@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_user_response.status_code == 201

    normal_headers = _login_headers(client, "blockuser@test.com", "supersecret123")

    list_response = client.get(
        "/api/v1/company-blocks/",
        headers=normal_headers,
    )
    assert list_response.status_code == 403

    create_response = client.post(
        "/api/v1/company-blocks/",
        json={
            "name": "Nope Block",
            "is_active": True,
            "company_id": company_id,
        },
        headers=normal_headers,
    )
    assert create_response.status_code == 403


def test_get_company_block_not_found(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.get(
        f"/api/v1/company-blocks/99999?company_id={company_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /company-blocks/ — validaciones adicionales
# ---------------------------------------------------------------------------


def test_create_company_block_name_too_short(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "X", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_create_company_block_invalid_company(client, auth_headers):
    response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque X", "is_active": True, "company_id": 99999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_company_block_name_is_normalized(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "bloque norte", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Bloque Norte"


def test_create_company_block_requires_auth(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Auth", "is_active": True, "company_id": company_id},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /company-blocks/ — filtros e include
# ---------------------------------------------------------------------------


def test_list_company_blocks_filter_company_id(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)

    # Crear otra empresa para tener bloques en diferentes compañías
    other_company = client.post(
        "/api/v1/companies/",
        json={"name": "Other Block Co", "company_type": "partner"},
        headers=auth_headers,
    )
    assert other_company.status_code == 201
    other_id = other_company.json()["id"]

    client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Filtro", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Otro", "is_active": True, "company_id": other_id},
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/company-blocks/?company_id={company_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["company_id"] == company_id for item in items)


def test_list_company_blocks_with_include_creator(client, auth_headers):
    response = client.get(
        "/api/v1/company-blocks/?include=creator",
        headers=auth_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    block_with_creator = next((b for b in items if b["creator"] is not None), None)
    assert block_with_creator is not None
    assert "id" in block_with_creator["creator"]


def test_list_company_blocks_with_include_company(client, auth_headers):
    response = client.get(
        "/api/v1/company-blocks/?include=company",
        headers=auth_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    block_with_company = next((b for b in items if b["company"] is not None), None)
    assert block_with_company is not None
    assert "id" in block_with_company["company"]
    assert "name" in block_with_company["company"]


# ---------------------------------------------------------------------------
# GET /company-blocks/{id} — auth, include, company_id requerido
# ---------------------------------------------------------------------------


def test_get_company_block_by_id_requires_auth(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Auth Get", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.get(f"/api/v1/company-blocks/{block_id}?company_id={company_id}")

    assert response.status_code == 401


def test_get_company_block_wrong_company_id(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Wrong Co", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    # Consultar con un company_id que no corresponde al bloque
    response = client.get(
        f"/api/v1/company-blocks/{block_id}?company_id=99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_get_company_block_missing_company_id(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Sin Co", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    # company_id es requerido; omitirlo debe retornar 422
    response = client.get(
        f"/api/v1/company-blocks/{block_id}",
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_get_company_block_with_include(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Include", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    # Sin include: company y creator son None
    plain = client.get(
        f"/api/v1/company-blocks/{block_id}?company_id={company_id}",
        headers=auth_headers,
    )
    assert plain.status_code == 200
    assert plain.json()["company"] is None
    assert plain.json()["creator"] is None

    # Con include=company,creator: ambos están poblados
    with_include = client.get(
        f"/api/v1/company-blocks/{block_id}?company_id={company_id}&include=company,creator",
        headers=auth_headers,
    )
    assert with_include.status_code == 200
    data = with_include.json()
    assert data["company"] is not None
    assert data["creator"] is not None


# ---------------------------------------------------------------------------
# PUT /company-blocks/{id}
# ---------------------------------------------------------------------------


def test_update_company_block(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Viejo", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/company-blocks/{block_id}",
        json={"name": "Bloque Nuevo", "is_active": False},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bloque Nuevo"
    assert data["is_active"] is False


def test_update_company_block_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/company-blocks/99999",
        json={"name": "No Existe"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_company_block_name_too_short(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Valid", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/company-blocks/{block_id}",
        json={"name": "X"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_update_company_block_name_is_normalized(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Norm", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/company-blocks/{block_id}",
        json={"name": "bloque actualizado"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Bloque Actualizado"


def test_update_company_block_invalid_company(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Empresa", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/company-blocks/{block_id}",
        json={"company_id": 99999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_company_block_requires_auth(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Auth Put", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/company-blocks/{block_id}",
        json={"name": "Sin Auth"},
    )

    assert response.status_code == 401


def test_non_admin_cannot_update_company_block(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Protegido", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    create_user = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "BlockUpdater",
            "email": "normalblockupdater@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_user.status_code == 201

    normal_headers = _login_headers(
        client, "normalblockupdater@test.com", "supersecret123"
    )

    response = client.put(
        f"/api/v1/company-blocks/{block_id}",
        json={"name": "Hackeado"},
        headers=normal_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /company-blocks/{id}
# ---------------------------------------------------------------------------


def test_delete_company_block(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Eliminar", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/company-blocks/{block_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["action"] == "deleted"
    assert payload["block"]["id"] == block_id

    get_response = client.get(
        f"/api/v1/company-blocks/{block_id}?company_id={company_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


def test_delete_company_block_not_found(client, auth_headers):
    response = client.delete(
        "/api/v1/company-blocks/99999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_company_block_requires_auth(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Auth Del", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/company-blocks/{block_id}")

    assert response.status_code == 401


def test_non_admin_cannot_delete_company_block(client, auth_headers):
    company_id = _admin_company_id(client, auth_headers)
    create_response = client.post(
        "/api/v1/company-blocks/",
        json={"name": "Bloque Prot Del", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    block_id = create_response.json()["id"]

    create_user = client.post(
        "/api/v1/users/",
        json={
            "name": "Normal",
            "last_name": "BlockDeleter",
            "email": "normalblockdeleter@test.com",
            "password": "supersecret123",
            "is_active": True,
            "company_id": company_id,
        },
        headers=auth_headers,
    )
    assert create_user.status_code == 201

    normal_headers = _login_headers(
        client, "normalblockdeleter@test.com", "supersecret123"
    )

    response = client.delete(
        f"/api/v1/company-blocks/{block_id}",
        headers=normal_headers,
    )

    assert response.status_code == 403
