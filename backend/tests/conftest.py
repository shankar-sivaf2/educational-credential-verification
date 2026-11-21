
"""Shared test fixtures. Tests use an in-memory SQLite database, never your real one."""
import os

# These must be set BEFORE the app modules are imported.
os.environ["JWT_SECRET"] = "test-secret-key-only-for-automated-tests-123456"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "TestPass@123"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402,F401
from app.api.deps import get_chain  # noqa: E402
from app.blockchain.contract_service import InMemoryChainClient  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import login_limiter, student_limiter  # noqa: E402
from app.services.auth_service import ensure_admin  # noqa: E402
from main import create_app  # noqa: E402

ADMIN_USER = "admin"
ADMIN_PASS = "TestPass@123"


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with factory() as db:
        ensure_admin(db, ADMIN_USER, ADMIN_PASS)

    yield factory

    engine.dispose()


@pytest.fixture()
def chain():
    """A simulated blockchain that follows the contract rules (tests only)."""
    return InMemoryChainClient()


@pytest.fixture()
def app(session_factory, chain):
    login_limiter.clear()
    student_limiter.clear()

    application = create_app()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_chain] = lambda: chain

    return application


@pytest.fixture()
def client(app):
    # No "with": we do not want the startup hook to touch the real database.
    return TestClient(app)


@pytest.fixture()
def auth_headers(client):
    resp = client.post(
        "/api/auth/login",
        json={
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
        },
    )

    assert resp.status_code == 200, resp.text

    return {
        "Authorization": f"Bearer {resp.json()['access_token']}"
    }


@pytest.fixture()
def sample_payload():
    return {
        "certificate_id": "CERT-2026-0001",
        "student_name": "Asha Raman",
        "student_id": "STU1001",
        "institution_name": "Demo Institute of Technology",
        "degree": "B.Tech",
        "department": "Computer Science and Engineering",
        "graduation_year": 2026,
    }
