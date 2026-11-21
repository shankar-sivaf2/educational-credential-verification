"""Certificate business logic (kept out of the API files on purpose)."""
from typing import Optional
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blockchain.contract_service import (
    ChainClient,
    ChainTransactionError,
    ChainUnavailableError,
)
from app.core.config import settings
from app.core.database import utcnow
from app.core.security import generate_access_code, hash_access_code, verify_access_code
from app.crypto.canonical import SCHEMA_VERSION
from app.crypto.hashing import (
    certificate_key,
    commitments_equal,
    compute_commitment,
    generate_salt,
)
from app.models.certificate import Certificate, CertificateStatus
from app.schemas.certificate import CertificateCreate
from app.services import audit_service
from app.utils.exceptions import AppError

NODE_DOWN_MESSAGE = (
    "The blockchain node is not reachable, so the certificate was NOT registered. "
    "Start the node, redeploy if needed, and try again."
)


def build_package(row: Certificate) -> dict:
    """The certificate file given to the student (includes the private salt)."""
    return {
        "schema": SCHEMA_VERSION,
        "certificate_id": row.certificate_id,
        "student_name": row.student_name,
        "student_id": row.student_id,
        "institution_name": row.institution_name,
        "degree": row.degree,
        "department": row.department,
        "graduation_year": row.graduation_year,
        "salt": row.salt,
    }


def verify_url(certificate_id: str) -> str:
    return f"{settings.frontend_origin}/verify?cert={quote(certificate_id, safe='')}"


def _mark_registered(db: Session, row: Certificate, tx_hash: Optional[str], issuer: str) -> None:
    row.status = CertificateStatus.REGISTERED
    row.tx_hash = tx_hash
    row.issuer_address = issuer
    row.failure_reason = None
    row.registered_at = utcnow()
    db.commit()


def _mark_failed(db: Session, row: Certificate, reason: str) -> None:
    row.status = CertificateStatus.FAILED
    row.failure_reason = reason[:255]
    db.commit()


def issue_certificate(
    db: Session, chain: ChainClient, data: CertificateCreate, actor: str
) -> tuple[Certificate, str]:
    """Validate, save, register the commitment on the blockchain, then mark REGISTERED.

    A certificate is only ever REGISTERED after the chain confirmed the transaction.
    If registration fails the row is kept as FAILED so the same ID can be retried.
    Returns (row, plaintext_access_code); the access code is shown once.
    """
    fields = data.model_dump()
    cert_id = fields["certificate_id"]
    key = certificate_key(cert_id)

    existing = db.scalar(select(Certificate).where(Certificate.certificate_id == cert_id))
    if existing is not None and existing.status in (CertificateStatus.REGISTERED, CertificateStatus.REVOKED):
        audit_service.log_event(db, "ISSUE", "REJECTED_DUPLICATE", actor, cert_id)
        raise AppError(409, "DUPLICATE_CERTIFICATE", f"Certificate '{cert_id}' already exists.")

    # Ask the chain first: this catches an outage before anything is saved, and detects
    # a commitment that was registered earlier although the database never recorded it.
    try:
        onchain = chain.get(key)
    except ChainUnavailableError as exc:
        audit_service.log_event(db, "ISSUE", "FAILED_BLOCKCHAIN_DOWN", actor, cert_id, str(exc))
        raise AppError(503, "BLOCKCHAIN_UNAVAILABLE", NODE_DOWN_MESSAGE) from exc

    salt = generate_salt()
    reconcile = False
    if onchain.exists:
        same_data = existing is not None and commitments_equal(
            compute_commitment(fields, existing.salt), onchain.commitment
        )
        if same_data:
            salt = existing.salt  # recover a half-finished earlier issuance
            reconcile = True
        else:
            audit_service.log_event(db, "ISSUE", "REJECTED_DUPLICATE_ON_CHAIN", actor, cert_id)
            raise AppError(
                409, "DUPLICATE_ON_CHAIN", f"Certificate '{cert_id}' is already registered on the blockchain."
            )

    access_code = generate_access_code()
    row = existing or Certificate(certificate_id=cert_id)
    for name, value in fields.items():
        setattr(row, name, value)
    row.salt = salt
    row.commitment = compute_commitment(fields, salt)
    row.chain_key = key
    row.access_code_hash = hash_access_code(access_code)
    row.status = CertificateStatus.PENDING
    row.failure_reason = None
    row.tx_hash = None
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # two requests raced for the same identifier
        db.rollback()
        raise AppError(409, "DUPLICATE_CERTIFICATE", f"Certificate '{cert_id}' already exists.")

    if reconcile:
        _mark_registered(db, row, None, onchain.issuer)
        audit_service.log_event(db, "ISSUE", "REGISTERED", actor, cert_id, "recovered existing chain record")
        return row, access_code

    try:
        tx = chain.register(key, row.commitment)
    except ChainUnavailableError as exc:
        _mark_failed(db, row, str(exc))
        audit_service.log_event(db, "ISSUE", "FAILED_BLOCKCHAIN_DOWN", actor, cert_id, str(exc))
        raise AppError(503, "BLOCKCHAIN_UNAVAILABLE", NODE_DOWN_MESSAGE) from exc
    except ChainTransactionError as exc:
        _mark_failed(db, row, str(exc))
        audit_service.log_event(db, "ISSUE", "FAILED_TX_REJECTED", actor, cert_id, str(exc))
        raise AppError(
            502, "BLOCKCHAIN_TX_FAILED", f"The blockchain rejected the registration: {exc}"
        ) from exc

    _mark_registered(db, row, tx.tx_hash, tx.issuer)
    audit_service.log_event(db, "ISSUE", "REGISTERED", actor, cert_id, f"tx {tx.tx_hash[:18]}")
    return row, access_code


def revoke_certificate(db: Session, chain: ChainClient, certificate_id: str, actor: str) -> Certificate:
    row = get_certificate(db, certificate_id)
    if row.status == CertificateStatus.REVOKED:
        raise AppError(409, "ALREADY_REVOKED", f"Certificate '{certificate_id}' is already revoked.")
    if row.status != CertificateStatus.REGISTERED:
        raise AppError(
            409,
            "NOT_REGISTERED",
            f"Only registered certificates can be revoked (current status: {row.status}).",
        )

    try:
        tx = chain.revoke(row.chain_key)
    except ChainUnavailableError as exc:
        audit_service.log_event(db, "REVOKE", "FAILED_BLOCKCHAIN_DOWN", actor, certificate_id, str(exc))
        raise AppError(503, "BLOCKCHAIN_UNAVAILABLE", NODE_DOWN_MESSAGE.replace("registered", "revoked")) from exc
    except ChainTransactionError as exc:
        audit_service.log_event(db, "REVOKE", "FAILED_TX_REJECTED", actor, certificate_id, str(exc))
        raise AppError(502, "BLOCKCHAIN_TX_FAILED", f"The blockchain rejected the revocation: {exc}") from exc

    row.status = CertificateStatus.REVOKED
    row.revoke_tx_hash = tx.tx_hash
    row.revoked_at = utcnow()
    db.commit()
    audit_service.log_event(db, "REVOKE", "REVOKED", actor, certificate_id, f"tx {tx.tx_hash[:18]}")
    return row


def get_certificate(db: Session, certificate_id: str) -> Certificate:
    row = db.scalar(select(Certificate).where(Certificate.certificate_id == certificate_id))
    if row is None:
        raise AppError(404, "NOT_FOUND", f"Certificate '{certificate_id}' was not found.")
    return row


def list_certificates(
    db: Session, status: Optional[str] = None, limit: int = 50, offset: int = 0
) -> tuple[list[Certificate], int]:
    query = select(Certificate)
    count_query = select(func.count()).select_from(Certificate)
    if status:
        query = query.where(Certificate.status == status)
        count_query = count_query.where(Certificate.status == status)
    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Certificate.id.desc()).limit(limit).offset(offset)).all()
    return list(items), total
def student_records(db: Session, student_id: str, access_code: str) -> list[Certificate]:
    """Certificates of this student whose access code matches (REGISTERED or REVOKED only)."""
    rows = db.scalars(
        select(Certificate)
        .where(
            Certificate.student_id == student_id,
            Certificate.status.in_([CertificateStatus.REGISTERED, CertificateStatus.REVOKED]),
        )
        .order_by(Certificate.id.desc())
    ).all()
    return [r for r in rows if verify_access_code(access_code, r.access_code_hash)]