
"""Module 3 tests: creating and retrieving certificate records."""
from sqlalchemy import select

from app.crypto.hashing import certificate_key, compute_commitment
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate


def issue(client, headers, payload):
    return client.post("/api/certificates", json=payload, headers=headers)


def test_issue_certificate_returns_package_and_access_code(client, auth_headers, sample_payload):
    resp = issue(client, auth_headers, sample_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["certificate"]["certificate_id"] == "CERT-2026-0001"
    assert body["certificate"]["status"] == "REGISTERED"  # confirmed on the (simulated) chain
    assert body["certificate"]["tx_hash"].startswith("0x")
    assert len(body["access_code"]) >= 10
    assert body["verify_url"].endswith("/verify?cert=CERT-2026-0001")

    package = body["package"]
    assert package["schema"] == "ecv-cert/1"
    assert len(package["salt"]) == 64

    # The stored commitment must be reproducible from the package alone.
    assert body["certificate"]["commitment"] == compute_commitment(package, package["salt"])


def test_retrieve_certificate_by_id(client, auth_headers, sample_payload):
    issue(client, auth_headers, sample_payload)
    resp = client.get("/api/certificates/CERT-2026-0001", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["student_name"] == "Asha Raman"
    assert "salt" not in resp.json()
    assert "access_code" not in resp.json()


def test_unknown_certificate_returns_404(client, auth_headers):
    resp = client.get("/api/certificates/DOES-NOT-EXIST", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_list_and_filter_certificates(client, auth_headers, sample_payload):
    issue(client, auth_headers, sample_payload)
    second = {**sample_payload, "certificate_id": "CERT-2026-0002", "student_id": "STU1002"}
    issue(client, auth_headers, second)

    resp = client.get("/api/certificates", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2
    assert resp.json()["items"][0]["certificate_id"] == "CERT-2026-0002"  # newest first

    registered = client.get("/api/certificates?status=REGISTERED", headers=auth_headers)
    assert registered.json()["total"] == 2

    revoked = client.get("/api/certificates?status=REVOKED", headers=auth_headers)
    assert revoked.json()["total"] == 0

    bad_filter = client.get("/api/certificates?status=HACKED", headers=auth_headers)
    assert bad_filter.status_code == 422


def test_duplicate_certificate_id_is_rejected(client, auth_headers, sample_payload):
    assert issue(client, auth_headers, sample_payload).status_code == 201
    again = issue(client, auth_headers, sample_payload)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "DUPLICATE_CERTIFICATE"


def test_issue_requires_login(client, sample_payload):
    resp = client.post("/api/certificates", json=sample_payload)
    assert resp.status_code == 401


def test_invalid_input_is_rejected(client, auth_headers, sample_payload):
    bad_inputs = [
        {**sample_payload, "graduation_year": 1800},
        {**sample_payload, "graduation_year": 3000},
        {**sample_payload, "certificate_id": "bad id with spaces!"},
        {**sample_payload, "certificate_id": "ab"},
        {**sample_payload, "student_name": "   "},
        {**sample_payload, "student_name": "Asha\nRaman"},
        {**sample_payload, "student_name": "Asha\u200bRaman"},  # zero-width character
        {**sample_payload, "student_id": ""},
        {**sample_payload, "degree": "x" * 500},
    ]
    for payload in bad_inputs:
        resp = issue(client, auth_headers, payload)
        assert resp.status_code == 422, payload

    missing = dict(sample_payload)
    del missing["department"]
    assert issue(client, auth_headers, missing).status_code == 422


def test_text_is_normalised_before_storing(client, auth_headers, sample_payload):
    messy = {**sample_payload, "student_name": "  Asha    Raman  "}
    resp = issue(client, auth_headers, messy)
    assert resp.status_code == 201
    assert resp.json()["certificate"]["student_name"] == "Asha Raman"


def test_record_persists_and_access_code_is_not_stored_in_plain_text(
    client, auth_headers, sample_payload, session_factory
):
    body = issue(client, auth_headers, sample_payload).json()
    with session_factory() as db:  # a brand-new session
        row = db.scalar(select(Certificate).where(Certificate.certificate_id == "CERT-2026-0001"))
        assert row is not None
        assert row.chain_key == certificate_key("CERT-2026-0001")
        assert row.access_code_hash != body["access_code"]
        assert body["access_code"] not in str(row.__dict__)


def test_issue_and_failed_attempts_are_audited(client, auth_headers, sample_payload, session_factory):
    issue(client, auth_headers, sample_payload)
    issue(client, auth_headers, sample_payload)  # duplicate

    with session_factory() as db:
        events = db.scalars(select(AuditLog).where(AuditLog.event_type == "ISSUE")).all()
        outcomes = sorted(e.outcome for e in events)
        assert outcomes == ["REGISTERED", "REJECTED_DUPLICATE"]
        # audit rows must not contain personal data
        assert all("Asha" not in (e.detail or "") for e in events)

    resp = client.get("/api/audit?event_type=ISSUE", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_audit_requires_login(client):
    assert client.get("/api/audit").status_code == 401


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["database"]["connected"] is True
