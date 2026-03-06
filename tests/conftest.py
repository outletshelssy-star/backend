import os

# Must be set before any app imports so get_settings() caches the correct env
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

import app.core.security.password as _pwd_module  # noqa: E402
import app.models  # noqa: E402
from app.core.security.password import hash_password  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.enums import CompanyType, UserType  # noqa: E402
from app.models.user import User  # noqa: E402

# Use minimal Argon2 parameters in tests to avoid slow hashing
_pwd_module._ph = PasswordHasher(
    time_cost=1,
    memory_cost=8,
    parallelism=1,
    hash_len=16,
    salt_len=8,
)


@pytest.fixture(scope="session")
def engine(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def session(engine):
    with Session(engine) as session:
        superadmin = User(
            name="Super",
            last_name="Admin",
            email="admin@local.dev",
            user_type=UserType.superadmin,
            is_active=True,
            password_hash=hash_password("supersecret123"),
        )
        session.add(superadmin)
        session.commit()
        session.refresh(superadmin)
        assert superadmin.id is not None

        company = Company(
            name="Frontera Energy",
            company_type=CompanyType.master,
            created_by_user_id=superadmin.id,
        )
        session.add(company)
        session.commit()
        session.refresh(company)

        superadmin.company_id = company.id
        session.add(superadmin)
        session.commit()
        yield session


@pytest.fixture()
def client(session):
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client, session: Session):
    admin = session.exec(select(User).where(User.email == "admin@local.dev")).first()

    if admin:
        admin.password_hash = hash_password("supersecret123")
    else:
        admin = User(
            name="Super",
            last_name="Admin",
            email="admin@local.dev",
            user_type=UserType.superadmin,
            is_active=True,
            password_hash=hash_password("supersecret123"),
        )
        session.add(admin)

    session.commit()
    session.refresh(admin)
    assert admin.id is not None

    company = session.exec(
        select(Company).where(Company.name == "Frontera Energy")
    ).first()
    if not company:
        company = Company(
            name="Frontera Energy",
            company_type=CompanyType.master,
            created_by_user_id=admin.id,
        )
        session.add(company)
        session.commit()
        session.refresh(company)

    if admin.company_id != company.id:
        admin.company_id = company.id
        session.add(admin)
        session.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@local.dev",
            "password": "supersecret123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200

    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
    }
