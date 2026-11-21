"""Module 5 tests: registering and revoking certificates through the blockchain layer.

Most tests use the simulated chain (InMemoryChainClient). The last tests exercise the
real web3 client: offline behaviour always, and a live round trip only when you start
a Hardhat node, deploy, and set RUN_CHAIN_INTEGRATION=1.
"""
import os
import secrets
from pathlib import Path

import pytest
from sqlalchemy import select

from app.blockchain.contract_service import (
    ChainTransactionError,
    ChainUnavailableError,
    InMemoryChainClient,
)
from app.crypto.hashing import certificate_key, compute_commitment
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate


def issue(client, headers, payload):
    return client.post("/api/certificates", json=payload, headers=headers)


# ------------------------------------------------------------------ issuing
def test_issue_registers_commitment_on_chain(client, auth_headers, sample_payload, chain):
    resp = issue(client, auth_headers, sample_payload)
    assert resp.status_code == 201, resp.text
    cert = resp.json()["certificate"]

    assert cert["status"] == "REGISTERED"
    assert cert["tx_hash"].startswith("0x") and len(cert["tx_hash"]) == 66
    assert cert["issuer_address"] == InMemoryChainClient.ISSUER
    assert cert["registered_at"].endswith("Z")

    onchain = chain.get(certificate_key("CERT-2026-0001"))
    assert onchain.exists
    assert onchain.commitment == cert["commitment"]
    package = resp.json()["package"]
    assert onchain.commitment == compute_commitment(package, package["salt"])


def test_chain_holds_no_personal_data(client, auth_headers, sample_payload, chain):
    issue(client, auth_headers, sample_payload)
    stored = repr(chain.records).lower()
    for secret_value in ("asha", "raman", "stu1001", "demo institute", "b.tech", "computer science"):
        assert secret_value not in stored
    # certificate ID is hashed too: only its key appears
    assert "cert-2026-0001" not in stored


def test_blockchain_down_blocks_issuing_and_saves_nothing(client, auth_headers, sample_payload, chain, session_factory):
    chain.available = False
    resp = issue(client, auth_headers, sample_payload)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "BLOCKCHAIN_UNAVAILABLE"
    assert "NOT registered" in resp.json()["error"]["message"]

    assert client.get("/api/certificates/CERT-2026-0001", headers=auth_headers).status_code == 404
    with session_factory() as db:
        events = db.scalars(select(AuditLog).where(AuditLog.event_type == "ISSUE")).all()
        assert [e.outcome for e in events] == ["FAILED_BLOCKCHAIN_DOWN"]


def test_rejected_transaction_is_failed_not_registered_and_can_be_retried(
    client, auth_headers, sample_payload, chain
):
    chain.fail_register = ChainTransactionError("boom")
    resp = issue(client, auth_headers, sample_payload)
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "BLOCKCHAIN_TX_FAILED"

    row = client.get("/api/certificates/CERT-2026-0001", headers=auth_headers).json()
    assert row["status"] == "FAILED"
    assert row["tx_hash"] is None
    assert "boom" in row["failure_reason"]
    assert chain.records == {}
    assert client.get("/api/certificates?status=REGISTERED", headers=auth_headers).json()["total"] == 0

    chain.fail_register = None  # the problem is fixed, retry the same certificate
    retry = issue(client, auth_headers, sample_payload)
    assert retry.status_code == 201
    assert retry.json()["certificate"]["status"] == "REGISTERED"
    assert retry.json()["certificate"]["failure_reason"] is None
    assert client.get("/api/certificates", headers=auth_headers).json()["total"] == 1  # same row reused


def test_outage_during_registration_marks_failed(client, auth_headers, sample_payload, chain):
    chain.fail_register = ChainUnavailableError("node went away")
    resp = issue(client, auth_headers, sample_payload)
    assert resp.status_code == 503
    row = client.get("/api/certificates/CERT-2026-0001", headers=auth_headers).json()
    assert row["status"] == "FAILED"


def test_signer_without_issuer_role_cannot_issue(client, auth_headers, sample_payload, chain):
    chain.signer_is_issuer = False
    resp = issue(client, auth_headers, sample_payload)
    assert resp.status_code == 502
    assert "AccessControlUnauthorizedAccount" in resp.json()["error"]["message"]
    assert chain.records == {}
    row = client.get("/api/certificates/CERT-2026-0001", headers=auth_headers).json()
    assert row["status"] == "FAILED"


def test_id_already_on_chain_is_rejected(client, auth_headers, sample_payload, chain):
    chain.register(certificate_key("CERT-2026-0001"), "0x" + "ab" * 32)  # registered elsewhere
    resp = issue(client, auth_headers, sample_payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE_ON_CHAIN"


def test_half_finished_issuance_is_recovered_without_a_second_transaction(
    client, auth_headers, sample_payload, chain, session_factory
):
    first = issue(client, auth_headers, sample_payload).json()
    assert chain.register_calls == 1

    # Simulate: the chain write succeeded but the database update was lost.
    with session_factory() as db:
        row = db.scalar(select(Certificate).where(Certificate.certificate_id == "CERT-2026-0001"))
        row.status = "PENDING"
        row.tx_hash = None
        db.commit()

    again = issue(client, auth_headers, sample_payload)
    assert again.status_code == 201
    assert again.json()["certificate"]["status"] == "REGISTERED"
    assert again.json()["package"]["salt"] == first["package"]["salt"]  # same commitment kept
    assert chain.register_calls == 1  # no duplicate transaction


# ---------------------------------------------------------------- revoking
def test_revoke_certificate(client, auth_headers, sample_payload, chain):
    issue(client, auth_headers, sample_payload)
    resp = client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "REVOKED"
    assert body["revoke_tx_hash"].startswith("0x")
    assert body["revoked_at"].endswith("Z")
    assert chain.get(certificate_key("CERT-2026-0001")).revoked is True


def test_revoke_twice_is_rejected(client, auth_headers, sample_payload):
    issue(client, auth_headers, sample_payload)
    client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    again = client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "ALREADY_REVOKED"


def test_revoke_unknown_certificate(client, auth_headers):
    resp = client.post("/api/certificates/NOPE-0001/revoke", headers=auth_headers)
    assert resp.status_code == 404


def test_revoke_requires_login(client, auth_headers, sample_payload):
    issue(client, auth_headers, sample_payload)
    assert client.post("/api/certificates/CERT-2026-0001/revoke").status_code == 401


def test_revoke_with_chain_down_keeps_certificate_registered(client, auth_headers, sample_payload, chain):
    issue(client, auth_headers, sample_payload)
    chain.available = False
    resp = client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    assert resp.status_code == 503
    chain.available = True
    row = client.get("/api/certificates/CERT-2026-0001", headers=auth_headers).json()
    assert row["status"] == "REGISTERED"
    assert chain.get(certificate_key("CERT-2026-0001")).revoked is False


def test_failed_certificate_cannot_be_revoked(client, auth_headers, sample_payload, chain):
    chain.fail_register = ChainTransactionError("boom")
    issue(client, auth_headers, sample_payload)
    resp = client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "NOT_REGISTERED"


def test_issue_and_revoke_are_audited(client, auth_headers, sample_payload, session_factory):
    issue(client, auth_headers, sample_payload)
    client.post("/api/certificates/CERT-2026-0001/revoke", headers=auth_headers)
    with session_factory() as db:
        pairs = [(e.event_type, e.outcome) for e in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert ("ISSUE", "REGISTERED") in pairs
    assert ("REVOKE", "REVOKED") in pairs


# ------------------------------------------------------------------ health
def test_health_reports_blockchain_status(client, chain):
    ok = client.get("/api/health").json()
    assert ok["status"] == "ok"
    assert ok["blockchain"]["connected"] is True
    assert ok["blockchain"]["signer_is_issuer"] is True

    chain.available = False
    down = client.get("/api/health").json()
    assert down["status"] == "degraded"
    assert down["blockchain"]["connected"] is False
    assert down["blockchain"]["error"]


# ------------------------------------------- simulated chain follows the rules
def test_simulated_chain_follows_contract_rules():
    chain = InMemoryChainClient()
    key, commitment = "0x" + "01" * 32, "0x" + "02" * 32

    assert chain.get(key).exists is False
    chain.register(key, commitment)
    assert chain.get(key).exists is True
    with pytest.raises(ChainTransactionError):
        chain.register(key, "0x" + "03" * 32)  # duplicate
    with pytest.raises(ChainTransactionError):
        chain.register("0x" + "04" * 32, "0x" + "00" * 32)  # zero commitment
    chain.revoke(key)
    with pytest.raises(ChainTransactionError):
        chain.revoke(key)  # already revoked
    with pytest.raises(ChainTransactionError):
        chain.revoke("0x" + "05" * 32)  # unknown


# ------------------------------------------- real web3 client (offline checks)
def _real_client(rpc_url="http://127.0.0.1:9", address="0x" + "11" * 20, key=""):
    pytest.importorskip("web3")
    from app.blockchain.web3_client import Web3ChainClient
    from app.core.config import ABI_FILE

    return Web3ChainClient(rpc_url, lambda: address, key, ABI_FILE, timeout=1)


def test_real_client_reports_unreachable_node():
    client = _real_client()
    health = client.health()
    assert health["connected"] is False
    assert "Cannot connect" in health["error"]
    with pytest.raises(ChainUnavailableError):
        client.get("0x" + "01" * 32)
    with pytest.raises(ChainUnavailableError):
        client.register("0x" + "01" * 32, "0x" + "02" * 32)


def test_real_client_reports_missing_contract_address():
    client = _real_client(address="")
    assert "not configured" in client.health()["error"]
    with pytest.raises(ChainUnavailableError):
        client.get("0x" + "01" * 32)


# --------------------------------- real web3 client against a live Hardhat node
@pytest.mark.skipif(
    os.environ.get("RUN_CHAIN_INTEGRATION") != "1",
    reason="needs a running Hardhat node + deployed contract; set RUN_CHAIN_INTEGRATION=1",
)
def test_live_round_trip_against_hardhat_node():
    pytest.importorskip("web3")
    from app.blockchain.contract_service import build_chain_client

    chain = build_chain_client()
    health = chain.health()
    assert health["connected"], health["error"]
    assert health["signer_is_issuer"] is True, "ISSUER_PRIVATE_KEY must be Hardhat account #0"

    key = certificate_key("LIVE-" + secrets.token_hex(6))
    commitment = "0x" + secrets.token_hex(32)

    assert chain.get(key).exists is False
    tx = chain.register(key, commitment)
    assert tx.tx_hash.startswith("0x") and tx.gas_used > 0

    record = chain.get(key)
    assert record.exists and record.commitment == commitment and record.revoked is False
    assert chain.is_authorized_issuer(record.issuer) is True

    with pytest.raises(ChainTransactionError):
        chain.register(key, commitment)  # duplicate must be rejected by the contract

    chain.revoke(key)
    assert chain.get(key).revoked is True
    with pytest.raises(ChainTransactionError):
        chain.revoke(key)