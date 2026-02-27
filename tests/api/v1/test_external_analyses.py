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
    """Lazy-create shared prerequisites (analysis type, block, terminal) once."""
    if _ids:
        return _ids

    me = client.get("/api/v1/users/me", headers=auth_headers).json()
    company_id = me["company_id"]

    # Analysis type with frequency (needed for next_due_at tests)
    atype = client.post(
        "/api/v1/external-analyses/types",
        json={
            "name": "EXT Test Analysis",
            "default_frequency_days": 30,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert atype.status_code == 201
    analysis_type_id = atype.json()["id"]

    # Block
    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "EXT Test Block", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert block.status_code == 201
    block_id = block.json()["id"]

    # Admin company for terminal
    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "EXT Admin Company", "company_type": "client"},
        headers=auth_headers,
    )
    assert admin_co.status_code == 201
    admin_company_id = admin_co.json()["id"]

    # Terminal
    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "EXT Test Terminal",
            "is_active": True,
            "has_lab": True,
            "block_id": block_id,
            "owner_company_id": company_id,
            "admin_company_id": admin_company_id,
            "terminal_code": "EXTX",
        },
        headers=auth_headers,
    )
    assert terminal.status_code == 201
    terminal_id = terminal.json()["id"]

    # Visitor user for permission tests
    client.post(
        "/api/v1/users/",
        json={
            "name": "Visitor",
            "last_name": "Ext",
            "email": "visitor.ext@test.com",
            "password": "supersecret123",
            "is_active": True,
            "user_type": "visitor",
            "company_id": company_id,
        },
        headers=auth_headers,
    )

    _ids.update(
        {
            "company_id": company_id,
            "analysis_type_id": analysis_type_id,
            "terminal_id": terminal_id,
        }
    )
    return _ids


def _create_record(client, auth_headers, ids: dict, **kwargs) -> int:
    payload = {"analysis_type_id": ids["analysis_type_id"], **kwargs}
    r = client.post(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        json=payload,
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# GET /external-analyses/types  (no auth required)
# ---------------------------------------------------------------------------


def test_list_types_no_auth_required(client, auth_headers):
    _setup(client, auth_headers)

    # Call without any auth header — must return 200, not 401
    response = client.get("/api/v1/external-analyses/types")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


# ---------------------------------------------------------------------------
# POST /external-analyses/types
# ---------------------------------------------------------------------------


def test_create_analysis_type(client, auth_headers):
    response = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT Create Test", "default_frequency_days": 90},
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "EXT Create Test"
    assert data["default_frequency_days"] == 90
    assert data["is_active"] is True


def test_create_analysis_type_duplicate_name(client, auth_headers):
    _setup(client, auth_headers)

    response = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT Test Analysis", "default_frequency_days": 30},
        headers=auth_headers,
    )

    assert response.status_code == 409


def test_create_analysis_type_requires_admin(client, auth_headers):
    _setup(client, auth_headers)
    visitor_headers = _login_headers(client, "visitor.ext@test.com")

    response = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT Visitor Attempt", "default_frequency_days": 0},
        headers=visitor_headers,
    )

    assert response.status_code == 403


def test_create_analysis_type_requires_auth(client):
    response = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT No Auth", "default_frequency_days": 0},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /external-analyses/types/{id}
# ---------------------------------------------------------------------------


def test_update_analysis_type(client, auth_headers):
    atype = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT Update Me", "default_frequency_days": 10},
        headers=auth_headers,
    )
    assert atype.status_code == 201
    type_id = atype.json()["id"]

    response = client.patch(
        f"/api/v1/external-analyses/types/{type_id}",
        json={"name": "EXT Updated Name", "default_frequency_days": 60},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "EXT Updated Name"
    assert data["default_frequency_days"] == 60


def test_update_analysis_type_not_found(client, auth_headers):
    response = client.patch(
        "/api/v1/external-analyses/types/999999",
        json={"name": "X"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_analysis_type_requires_admin(client, auth_headers):
    ids = _setup(client, auth_headers)
    visitor_headers = _login_headers(client, "visitor.ext@test.com")

    response = client.patch(
        f"/api/v1/external-analyses/types/{ids['analysis_type_id']}",
        json={"is_active": False},
        headers=visitor_headers,
    )

    assert response.status_code == 403


def test_update_analysis_type_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.patch(
        f"/api/v1/external-analyses/types/{ids['analysis_type_id']}",
        json={"is_active": False},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /external-analyses/types/{id}
# ---------------------------------------------------------------------------


def test_delete_analysis_type(client, auth_headers):
    atype = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT To Delete", "default_frequency_days": 0},
        headers=auth_headers,
    )
    assert atype.status_code == 201
    type_id = atype.json()["id"]

    response = client.delete(
        f"/api/v1/external-analyses/types/{type_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


def test_delete_analysis_type_not_found(client, auth_headers):
    response = client.delete(
        "/api/v1/external-analyses/types/999999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_analysis_type_in_use(client, auth_headers):
    """Deleting a type already configured for a terminal must return 409."""
    ids = _setup(client, auth_headers)

    # Create a type and configure it for a terminal → makes it "in use"
    atype = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT Blocked Type", "default_frequency_days": 0},
        headers=auth_headers,
    )
    assert atype.status_code == 201
    blocked_type_id = atype.json()["id"]

    client.post(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": blocked_type_id, "is_active": True},
        headers=auth_headers,
    )

    response = client.delete(
        f"/api/v1/external-analyses/types/{blocked_type_id}",
        headers=auth_headers,
    )

    assert response.status_code == 409


def test_delete_analysis_type_requires_admin(client, auth_headers):
    _setup(client, auth_headers)
    visitor_headers = _login_headers(client, "visitor.ext@test.com")

    atype = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT Visitor Del", "default_frequency_days": 0},
        headers=auth_headers,
    )
    type_id = atype.json()["id"]

    response = client.delete(
        f"/api/v1/external-analyses/types/{type_id}",
        headers=visitor_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /external-analyses/terminal/{id}
# ---------------------------------------------------------------------------


def test_list_terminal_analyses(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.get(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "analysis_type_id" in item
    assert "frequency_days" in item
    assert "is_active" in item


def test_list_terminal_analyses_terminal_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/external-analyses/terminal/999999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_list_terminal_analyses_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.get(f"/api/v1/external-analyses/terminal/{ids['terminal_id']}")

    assert response.status_code == 401


def test_list_terminal_analyses_next_due_at_computed(client, auth_headers):
    """After creating a record for a type with frequency_days > 0, next_due_at is set."""
    ids = _setup(client, auth_headers)

    _create_record(client, auth_headers, ids)

    response = client.get(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    items = response.json()["items"]
    matching = [i for i in items if i["analysis_type_id"] == ids["analysis_type_id"]]
    assert len(matching) == 1
    assert matching[0]["last_performed_at"] is not None
    assert matching[0]["next_due_at"] is not None


# ---------------------------------------------------------------------------
# POST /external-analyses/terminal/{id}  (upsert config)
# ---------------------------------------------------------------------------


def test_upsert_terminal_analysis(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": ids["analysis_type_id"], "is_active": True},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["terminal_id"] == ids["terminal_id"]
    assert data["analysis_type_id"] == ids["analysis_type_id"]
    assert data["is_active"] is True


def test_upsert_terminal_analysis_updates_existing(client, auth_headers):
    """Second POST to same terminal+type updates instead of creating a duplicate."""
    ids = _setup(client, auth_headers)

    client.post(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": ids["analysis_type_id"], "is_active": True},
        headers=auth_headers,
    )

    response = client.post(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": ids["analysis_type_id"], "is_active": False},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_upsert_terminal_analysis_terminal_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        "/api/v1/external-analyses/terminal/999999",
        json={"analysis_type_id": ids["analysis_type_id"], "is_active": True},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_upsert_terminal_analysis_type_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": 999999, "is_active": True},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_upsert_terminal_analysis_requires_admin(client, auth_headers):
    ids = _setup(client, auth_headers)
    visitor_headers = _login_headers(client, "visitor.ext@test.com")

    response = client.post(
        f"/api/v1/external-analyses/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": ids["analysis_type_id"], "is_active": True},
        headers=visitor_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /external-analyses/records/terminal/{id}
# ---------------------------------------------------------------------------


def test_create_record(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        json={
            "analysis_type_id": ids["analysis_type_id"],
            "report_number": "RPT-001",
            "result_value": 34.5,
            "result_unit": "API",
            "method": "ASTM D1298",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["terminal_id"] == ids["terminal_id"]
    assert data["analysis_type_id"] == ids["analysis_type_id"]
    assert data["report_number"] == "RPT-001"
    assert data["result_value"] == 34.5
    assert data["analysis_type_name"] is not None


def test_create_record_with_company(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        json={
            "analysis_type_id": ids["analysis_type_id"],
            "analysis_company_id": ids["company_id"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["analysis_company_id"] == ids["company_id"]
    assert data["analysis_company_name"] is not None


def test_create_record_invalid_type(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": 999999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_record_invalid_company(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        json={
            "analysis_type_id": ids["analysis_type_id"],
            "analysis_company_id": 999999,
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_record_terminal_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        "/api/v1/external-analyses/records/terminal/999999",
        json={"analysis_type_id": ids["analysis_type_id"]},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_record_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.post(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": ids["analysis_type_id"]},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /external-analyses/records/terminal/{id}
# ---------------------------------------------------------------------------


def test_list_records(client, auth_headers):
    ids = _setup(client, auth_headers)
    _create_record(client, auth_headers, ids, report_number="RPT-LIST")

    response = client.get(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["analysis_type_name"] is not None


def test_list_records_filter_by_type(client, auth_headers):
    ids = _setup(client, auth_headers)

    # Create a second type and a record for it
    atype2 = client.post(
        "/api/v1/external-analyses/types",
        json={"name": "EXT Filter Type", "default_frequency_days": 0},
        headers=auth_headers,
    )
    assert atype2.status_code == 201
    type2_id = atype2.json()["id"]

    client.post(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}",
        json={"analysis_type_id": type2_id},
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}?analysis_type_id={type2_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert all(i["analysis_type_id"] == type2_id for i in data["items"])


def test_list_records_terminal_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/external-analyses/records/terminal/999999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_list_records_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)

    response = client.get(
        f"/api/v1/external-analyses/records/terminal/{ids['terminal_id']}"
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /external-analyses/records/{id}
# ---------------------------------------------------------------------------


def test_update_record(client, auth_headers):
    ids = _setup(client, auth_headers)
    record_id = _create_record(client, auth_headers, ids, notes="original")

    response = client.patch(
        f"/api/v1/external-analyses/records/{record_id}",
        json={"notes": "updated", "result_value": 42.0},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "updated"
    assert data["result_value"] == 42.0


def test_update_record_not_found(client, auth_headers):
    response = client.patch(
        "/api/v1/external-analyses/records/999999",
        json={"notes": "x"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_record_invalid_type(client, auth_headers):
    ids = _setup(client, auth_headers)
    record_id = _create_record(client, auth_headers, ids)

    response = client.patch(
        f"/api/v1/external-analyses/records/{record_id}",
        json={"analysis_type_id": 999999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_record_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    record_id = _create_record(client, auth_headers, ids)

    response = client.patch(
        f"/api/v1/external-analyses/records/{record_id}",
        json={"notes": "x"},
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /external-analyses/records/{id}
# ---------------------------------------------------------------------------


def test_delete_record(client, auth_headers):
    ids = _setup(client, auth_headers)
    record_id = _create_record(client, auth_headers, ids)

    response = client.delete(
        f"/api/v1/external-analyses/records/{record_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


def test_delete_record_verifies_gone(client, auth_headers):
    ids = _setup(client, auth_headers)
    record_id = _create_record(client, auth_headers, ids)

    client.delete(
        f"/api/v1/external-analyses/records/{record_id}",
        headers=auth_headers,
    )

    response = client.patch(
        f"/api/v1/external-analyses/records/{record_id}",
        json={"notes": "ghost"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_record_not_found(client, auth_headers):
    response = client.delete(
        "/api/v1/external-analyses/records/999999",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_record_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    record_id = _create_record(client, auth_headers, ids)

    response = client.delete(f"/api/v1/external-analyses/records/{record_id}")

    assert response.status_code == 401
