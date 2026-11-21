"""Module 6 tests: employer verification, QR status lookup, student records, QR image."""
import json

from sqlalchemy import select

from app.blockchain.contract_service import InMemoryChainClient
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate


def issue(client, headers, payload):
    resp = client.post("/api/certificates", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def verify(client, package):
    return client.post("/api/verify", json=package)


# ----------------------------------------------------------- core outcomes
def test_valid_certificate_is_authentic(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    resp = verify(client, package)  # note: no login needed
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "AUTHENTIC_VALID"
    assert body["valid"] is True
    assert body["checks"] == {
        "registered": True,
        "commitment_matches": True,
        "issuer_authorized": True,
        "not_revoked": True,
    }
    assert body["issuer"] == InMemoryChainClient.ISSUER
    assert body["registered_at"].endswith("Z")
    assert "does not by itself prove" in body["note"]


def test_modified_certificate_is_rejected(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    tampered_values = {
        "student_name": "Mallory Forger",
        "student_id": "STU9999",
        "institution_name": "Fake University",
        "degree": "PhD",
        "department": "Law",
        "graduation_year": 2020,
    }
    for field, new_value in tampered_values.items():
        body = verify(client, {**package, field: new_value}).json()
        assert body["status"] == "COMMITMENT_MISMATCH", field
        assert body["valid"] is False
        assert body["checks"]["registered"] is True
        assert body["checks"]["commitment_matches"] is False


def test_supplying_a_different_salt_cannot_fake_a_match(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    forged = {**package, "salt": "cd" * 32}
    assert verify(client, forged).json()["status"] == "COMMITMENT_MISMATCH"


def test_case_change_is_a_mismatch_but_extra_spaces_are_not(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    assert verify(client, {**package, "student_name": "ASHA RAMAN"}).json()["status"] == "COMMITMENT_MISMATCH"
    spaced = {**package, "student_name": "  Asha   Raman "}
    assert verify(client, spaced).json()["status"] == "AUTHENTIC_VALID"


def test_unknown_certificate_is_rejected(client, sample_payload, auth_headers):
    package = issue(client, auth_headers, sample_payload)["package"]
    unknown = {**package, "certificate_id": "CERT-NEVER-ISSUED"}
    body = verify(client, unknown).json()
    assert body["status"] == "UNKNOWN"
    assert body["valid"] is False
    assert body["checks"]["registered"] is False


def test_revoked_certificate_is_not_reported_valid(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    body = verify(client, package).json()
    assert body["status"] == "REVOKED"
    assert body["valid"] is False
    assert body["checks"]["commitment_matches"] is True
    assert body["checks"]["not_revoked"] is False


def test_unauthorised_issuer_is_flagged(client, auth_headers, sample_payload, chain):
    package = issue(client, auth_headers, sample_payload)["package"]
    chain.issuer_authorized = False  # the institution lost its issuer role on-chain
    body = verify(client, package).json()
    assert body["status"] == "INVALID_ISSUER"
    assert body["valid"] is False
    assert body["checks"]["issuer_authorized"] is False


def test_service_unavailable_is_reported_honestly(client, auth_headers, sample_payload, chain):
    package = issue(client, auth_headers, sample_payload)["package"]
    chain.available = False
    resp = verify(client, package)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "SERVICE_UNAVAILABLE"
    assert body["valid"] is False
    assert body["checks"] == {
        "registered": None,
        "commitment_matches": None,
        "issuer_authorized": None,
        "not_revoked": None,
    }


def test_verification_does_not_depend_on_the_local_database(
    client, auth_headers, sample_payload, session_factory
):
    package = issue(client, auth_headers, sample_payload)["package"]
    with session_factory() as db:  # the institution's database is wiped
        db.query(Certificate).delete()
        db.commit()
    assert verify(client, package).json()["status"] == "AUTHENTIC_VALID"


# ----------------------------------------------------------- invalid input
def test_invalid_verification_input_is_rejected(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]

    bad_salt = verify(client, {**package, "salt": "not-hex"})
    assert bad_salt.status_code == 422

    short_salt = verify(client, {**package, "salt": "ab" * 10})
    assert short_salt.status_code == 422

    wrong_schema = verify(client, {**package, "schema": "other/9"})
    assert wrong_schema.status_code == 422

    missing = {k: v for k, v in package.items() if k != "degree"}
    assert verify(client, missing).status_code == 422

    blank = verify(client, {**package, "student_name": "   "})
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "INVALID_INPUT"

    assert verify(client, {**package, "graduation_year": "soon"}).status_code == 422


def test_verification_is_audited_without_personal_data(client, auth_headers, sample_payload, session_factory):
    package = issue(client, auth_headers, sample_payload)["package"]
    verify(client, package)
    verify(client, {**package, "degree": "PhD"})
    with session_factory() as db:
        events = db.scalars(select(AuditLog).where(AuditLog.event_type == "VERIFY")).all()
        assert sorted(e.outcome for e in events) == ["AUTHENTIC_VALID", "COMMITMENT_MISMATCH"]
        assert all(e.actor == "anonymous" for e in events)
        assert all("Asha" not in (e.detail or "") for e in events)


# ------------------------------------------------------------ file upload
def upload(client, content: bytes, filename="certificate.json", content_type="application/json"):
    return client.post("/api/verify/upload", files={"file": (filename, content, content_type)})


def test_upload_valid_certificate_file(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    resp = upload(client, json.dumps(package).encode())
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "AUTHENTIC_VALID"


def test_upload_tampered_file_fails(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    package["degree"] = "PhD"
    assert upload(client, json.dumps(package).encode()).json()["status"] == "COMMITMENT_MISMATCH"


def test_upload_rejects_bad_files(client, auth_headers, sample_payload):
    package = issue(client, auth_headers, sample_payload)["package"]
    good = json.dumps(package).encode()

    assert upload(client, good, filename="certificate.exe").status_code == 400
    assert upload(client, good, filename="certificate.json", content_type="image/png").status_code == 400
    assert upload(client, b"{not json", ).status_code == 400
    assert upload(client, b"\xff\xfe\x00bad bytes").status_code == 400
    assert upload(client, b"[1, 2, 3]").status_code == 400

    too_big = upload(client, b'{"x": "' + b"a" * (70 * 1024) + b'"}')
    assert too_big.status_code == 413
    assert too_big.json()["error"]["code"] == "FILE_TOO_LARGE"

    incomplete = upload(client, json.dumps({"certificate_id": "CERT-1"}).encode())
    assert incomplete.status_code == 422
    assert incomplete.json()["error"]["code"] == "INVALID_CERTIFICATE_FILE"


# -------------------------------------------------------- QR status lookup
def test_status_lookup_by_certificate_id(client, auth_headers, sample_payload):
    issue(client, auth_headers, sample_payload)
    body = client.get("/api/verify/status/CERT-2026-0001").json()  # public
    assert body["status"] == "REGISTERED"
    assert "does NOT check the certificate contents" in body["message"]
    # no personal data may appear in this public response
    assert set(body) == {"certificate_id", "status", "message", "issuer", "registered_at"}

    client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    assert client.get("/api/verify/status/CERT-2026-0001").json()["status"] == "REVOKED"


def test_status_lookup_unknown_and_outage(client, chain):
    assert client.get("/api/verify/status/NOPE-1234").json()["status"] == "UNKNOWN"
    chain.available = False
    assert client.get("/api/verify/status/NOPE-1234").json()["status"] == "SERVICE_UNAVAILABLE"


def test_status_lookup_rejects_overlong_ids(client):
    assert client.get("/api/verify/status/" + "A" * 65).status_code == 422


# ---------------------------------------------------------- student records
def test_student_sees_own_certificate_and_it_verifies(client, auth_headers, sample_payload):
    issued = issue(client, auth_headers, sample_payload)
    resp = client.post(
        "/api/student/records",
        json={"student_id": "STU1001", "access_code": issued["access_code"]},
    )
    assert resp.status_code == 200, resp.text
    records = resp.json()["records"]
    assert len(records) == 1
    assert records[0]["certificate"]["certificate_id"] == "CERT-2026-0001"
    assert records[0]["certificate"]["status"] == "REGISTERED"
    assert records[0]["verify_url"].endswith("/verify?cert=CERT-2026-0001")
    assert "access_code_hash" not in json.dumps(resp.json())

    # the package the student received verifies as authentic
    assert verify(client, records[0]["package"]).json()["status"] == "AUTHENTIC_VALID"


def test_student_access_needs_the_right_code_and_id(client, auth_headers, sample_payload):
    issued = issue(client, auth_headers, sample_payload)
    wrong_code = client.post("/api/student/records", json={"student_id": "STU1001", "access_code": "wrong"})
    wrong_id = client.post(
        "/api/student/records", json={"student_id": "STU2002", "access_code": issued["access_code"]}
    )
    for resp in (wrong_code, wrong_id):
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NO_RECORDS"
    # identical message, so valid student IDs cannot be discovered
    assert wrong_code.json() == wrong_id.json()


def test_student_cannot_see_another_students_certificate(client, auth_headers, sample_payload):
    first = issue(client, auth_headers, sample_payload)
    second_payload = {**sample_payload, "certificate_id": "CERT-2026-0002", "student_id": "STU2002",
                      "student_name": "Ravi Kumar"}
    issue(client, auth_headers, second_payload)

    resp = client.post(
        "/api/student/records", json={"student_id": "STU2002", "access_code": first["access_code"]}
    )
    assert resp.status_code == 404


def test_student_sees_revoked_status(client, auth_headers, sample_payload):
    issued = issue(client, auth_headers, sample_payload)
    client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    resp = client.post(
        "/api/student/records", json={"student_id": "STU1001", "access_code": issued["access_code"]}
    )
    assert resp.json()["records"][0]["certificate"]["status"] == "REVOKED"


def test_student_access_is_rate_limited(client, auth_headers, sample_payload):
    issued = issue(client, auth_headers, sample_payload)
    for _ in range(5):
        client.post("/api/student/records", json={"student_id": "STU1001", "access_code": "guess"})
    resp = client.post(
        "/api/student/records", json={"student_id": "STU1001", "access_code": issued["access_code"]}
    )
    assert resp.status_code == 429


# ------------------------------------------------------------------ QR image
def test_admin_can_download_qr_png(client, auth_headers, sample_payload):
    issue(client, auth_headers, sample_payload)
    resp = client.get("/api/certificates/CERT-2026-0001/qr.png", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG")


def test_qr_requires_login_and_known_certificate(client, auth_headers, sample_payload):
    issue(client, auth_headers, sample_payload)
    assert client.get("/api/certificates/CERT-2026-0001/qr.png").status_code == 401
    assert client.get("/api/certificates/NOPE-0001/qr.png", headers=auth_headers).status_code == 404


# ------------------------------------------------------ whole workflow
def test_full_workflow_issue_student_verify_revoke_verify(client, auth_headers, sample_payload):
    issued = issue(client, auth_headers, sample_payload)                                   # 1. issue
    student = client.post(                                                                   # 2. student
        "/api/student/records",
        json={"student_id": "STU1001", "access_code": issued["access_code"]},
    ).json()["records"][0]["package"]
    assert verify(client, student).json()["status"] == "AUTHENTIC_VALID"                   # 3. employer
    assert verify(client, {**student, "degree": "PhD"}).json()["status"] == "COMMITMENT_MISMATCH"
    client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)           # 4. revoke
    assert verify(client, student).json()["status"] == "REVOKED"                           # 5. re-check