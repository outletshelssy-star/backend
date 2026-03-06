from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.core.security.password import hash_password
from app.models.enums import UserType
from app.models.user import User

_ids: dict = {}


def _setup(client, auth_headers) -> dict:
    if _ids:
        return _ids

    me = client.get("/api/v1/users/me", headers=auth_headers).json()
    company_id = me["company_id"]

    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "SampleTest Block", "is_active": True, "company_id": company_id},
        headers=auth_headers,
    )
    assert block.status_code == 201

    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "SampleTest Admin Co", "company_type": "client"},
        headers=auth_headers,
    )
    assert admin_co.status_code == 201

    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "SampleTest Terminal",
            "terminal_code": "SMP",
            "is_active": True,
            "has_lab": True,
            "block_id": block.json()["id"],
            "owner_company_id": company_id,
            "admin_company_id": admin_co.json()["id"],
        },
        headers=auth_headers,
    )
    assert terminal.status_code == 201

    _ids.update(
        {
            "company_id": company_id,
            "terminal_id": terminal.json()["id"],
        }
    )
    return _ids


def _sample_payload(ids: dict) -> dict:
    return {
        "terminal_id": ids["terminal_id"],
        "identifier": "MUESTRA-001",
        "analyses": [
            {
                "analysis_type": "api_astm_1298",
                "temp_obs_f": 70.0,
                "lectura_api": 28.5,
            }
        ],
    }


def _user_auth_headers(client, session) -> dict:
    user = session.exec(select(User).where(User.email == "sample.user@local.dev")).first()
    if user:
        user.password_hash = hash_password("usersecret123")
        user.user_type = UserType.user
        user.is_active = True
    else:
        user = User(
            name="Sample",
            last_name="User",
            email="sample.user@local.dev",
            user_type=UserType.user,
            is_active=True,
            password_hash=hash_password("usersecret123"),
        )
        session.add(user)
    session.commit()
    session.refresh(user)
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "sample.user@local.dev",
            "password": "usersecret123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
    }


# ---------------------------------------------------------------------------
# POST /samples/
# ---------------------------------------------------------------------------


def test_create_sample(client, auth_headers):
    ids = _setup(client, auth_headers)
    analyzed_at = "2026-02-01T00:00:00Z"
    payload = _sample_payload(ids)
    payload["analyzed_at"] = analyzed_at
    response = client.post(
        "/api/v1/samples/",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["terminal_id"] == ids["terminal_id"]
    assert data["identifier"] == "MUESTRA-001"
    assert data["analyzed_at"] == analyzed_at
    assert data["code"].startswith("SMP-")
    assert len(data["analyses"]) == 1
    assert data["analyses"][0]["analysis_type"] == "api_astm_1298"
    assert data["analyses"][0]["api_60f"] is not None
    _ids["sample_id"] = data["id"]
    _ids["sample_sequence"] = data["sequence"]


def test_create_sample_increments_sequence(client, auth_headers):
    ids = _setup(client, auth_headers)
    r1 = client.post("/api/v1/samples/", json=_sample_payload(ids), headers=auth_headers)
    r2 = client.post("/api/v1/samples/", json=_sample_payload(ids), headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r2.json()["sequence"] == r1.json()["sequence"] + 1


def test_create_sample_empty_identifier(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _sample_payload(ids)
    payload["identifier"] = "   "
    response = client.post("/api/v1/samples/", json=payload, headers=auth_headers)
    assert response.status_code == 400


def test_create_sample_terminal_not_found(client, auth_headers):
    ids = _setup(client, auth_headers)
    payload = _sample_payload(ids)
    payload["terminal_id"] = 999999
    response = client.post("/api/v1/samples/", json=payload, headers=auth_headers)
    assert response.status_code == 404


def test_create_sample_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.post("/api/v1/samples/", json=_sample_payload(ids))
    assert response.status_code == 401


def test_create_sample_rejects_analyzed_at_older_than_72_hours_for_user(
    client, auth_headers, session
):
    ids = _setup(client, auth_headers)
    user_headers = _user_auth_headers(client, session)
    payload = _sample_payload(ids)
    payload["analyzed_at"] = (datetime.now(UTC) - timedelta(hours=73)).isoformat()
    response = client.post("/api/v1/samples/", json=payload, headers=user_headers)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /samples/terminal/{terminal_id}
# ---------------------------------------------------------------------------


def test_list_samples(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(
        f"/api/v1/samples/terminal/{ids['terminal_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_list_samples_empty_terminal(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Create fresh terminal with no samples
    block = client.post(
        "/api/v1/company-blocks/",
        json={"name": "SampleEmpty Block", "is_active": True, "company_id": ids["company_id"]},
        headers=auth_headers,
    )
    admin_co = client.post(
        "/api/v1/companies/",
        json={"name": "SampleEmpty Co", "company_type": "client"},
        headers=auth_headers,
    )
    terminal = client.post(
        "/api/v1/company-terminals/",
        json={
            "name": "SampleEmpty Terminal",
            "terminal_code": "SMPE",
            "is_active": True,
            "has_lab": True,
            "block_id": block.json()["id"],
            "owner_company_id": ids["company_id"],
            "admin_company_id": admin_co.json()["id"],
        },
        headers=auth_headers,
    )
    assert terminal.status_code == 201
    empty_terminal_id = terminal.json()["id"]

    response = client.get(
        f"/api/v1/samples/terminal/{empty_terminal_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json().get("message") == "No records found"


def test_list_samples_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.get(f"/api/v1/samples/terminal/{ids['terminal_id']}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /samples/{sample_id}
# ---------------------------------------------------------------------------


def test_update_sample(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "sample_id" in ids
    response = client.patch(
        f"/api/v1/samples/{ids['sample_id']}",
        json={
            "product_name": "Crudo Liviano",
            "analyses": [
                {
                    "analysis_type": "api_astm_1298",
                    "temp_obs_f": 72.0,
                    "lectura_api": 30.0,
                }
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_name"] == "Crudo Liviano"
    assert data["analyses"][0]["lectura_api"] == 30.0
    assert data["analyses"][0]["api_60f"] is not None


def test_update_sample_not_found(client, auth_headers):
    response = client.patch(
        "/api/v1/samples/999999",
        json={"product_name": "No existe"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_sample_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.patch(
        f"/api/v1/samples/{ids['sample_id']}",
        json={"product_name": "No auth"},
    )
    assert response.status_code == 401


def test_update_sample_rejects_analyzed_at_older_than_72_hours_for_user(
    client, auth_headers, session
):
    ids = _setup(client, auth_headers)
    user_headers = _user_auth_headers(client, session)
    create_response = client.post(
        "/api/v1/samples/",
        json=_sample_payload(ids),
        headers=user_headers,
    )
    assert create_response.status_code == 201
    sample_id = create_response.json()["id"]
    response = client.patch(
        f"/api/v1/samples/{sample_id}",
        json={"analyzed_at": (datetime.now(UTC) - timedelta(hours=73)).isoformat()},
        headers=user_headers,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /samples/{sample_id}
# ---------------------------------------------------------------------------


def test_delete_sample_only_latest(client, auth_headers):
    ids = _setup(client, auth_headers)
    # Create a brand-new sample to delete (it must be the latest)
    create = client.post(
        "/api/v1/samples/",
        json={
            "terminal_id": ids["terminal_id"],
            "identifier": "MUESTRA-TO-DELETE",
            "analyses": [],
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    sample_id = create.json()["id"]

    response = client.delete(
        f"/api/v1/samples/{sample_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204


def test_delete_sample_not_found(client, auth_headers):
    response = client.delete(
        "/api/v1/samples/999999",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_sample_not_latest_rejected(client, auth_headers):
    ids = _setup(client, auth_headers)
    assert "sample_id" in ids

    # Create a newer sample so ids["sample_id"] is no longer the latest
    newer = client.post(
        "/api/v1/samples/",
        json={
            "terminal_id": ids["terminal_id"],
            "identifier": "MUESTRA-NEWER",
            "analyses": [],
        },
        headers=auth_headers,
    )
    assert newer.status_code == 201

    response = client.delete(
        f"/api/v1/samples/{ids['sample_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_delete_sample_requires_auth(client, auth_headers):
    ids = _setup(client, auth_headers)
    response = client.delete(f"/api/v1/samples/{ids['sample_id']}")
    assert response.status_code == 401
