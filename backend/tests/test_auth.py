"""Module 3 tests: administrator login and route protection."""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from tests.conftest import ADMIN_PASS, ADMIN_USER


def test_login_success_returns_token(client):
    resp = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["username"] == ADMIN_USER
    assert len(body["access_token"]) > 20


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "whatever"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_with_valid_token(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == ADMIN_USER


def test_protected_routes_need_a_token(client):
    for path in ("/api/certificates", "/api/audit", "/api/auth/me"):
        resp = client.get(path)
        assert resp.status_code == 401, path
        assert resp.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_garbage_token_is_rejected(client):
    resp = client.get("/api/certificates", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_TOKEN"


def test_expired_token_is_rejected(client):
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode(
        {"sub": ADMIN_USER, "role": "admin", "iat": past - timedelta(hours=1), "exp": past},
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = client.get("/api/certificates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_signed_with_wrong_secret_is_rejected(client):
    token = jwt.encode(
        {"sub": ADMIN_USER, "role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "some-other-secret-that-is-long-enough-123456",
        algorithm="HS256",
    )
    resp = client.get("/api/certificates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_non_admin_role_is_forbidden(client):
    token = jwt.encode(
        {"sub": ADMIN_USER, "role": "student", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = client.get("/api/certificates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_login_is_locked_after_repeated_failures(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": ADMIN_USER, "password": "bad"})
    resp = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"