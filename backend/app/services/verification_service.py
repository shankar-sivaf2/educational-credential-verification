"""Certificate verification.

The verdict comes ONLY from the blockchain plus the certificate data the verifier supplies.
The local database is never consulted, so a verifier does not have to trust the institution's
own server, and a verifier cannot "prove" a certificate by supplying a hash: the backend
recomputes the commitment itself from the supplied fields and salt.

What a positive result means: the supplied data is exactly what an account that is currently
an authorised issuer registered, and it has not been revoked. It does not, by itself, prove
that the underlying educational claim is true.
"""
from datetime import datetime, timezone
from typing import Optional

from app.blockchain.contract_service import ChainClient, ChainUnavailableError
from app.crypto.canonical import CanonicalizationError
from app.crypto.hashing import certificate_key, commitments_equal, compute_commitment
from app.schemas.certificate import CertificatePackage
from app.schemas.verification import (
    StatusLookupResult,
    VerificationChecks,
    VerificationResult,
    VerificationStatus,
)
from app.utils.exceptions import AppError

NOTE = (
    "Verification confirms that the data is unchanged since it was registered by an authorised "
    "issuer account and shows its current status. It does not by itself prove that the "
    "underlying educational claim is true."
)

MESSAGES = {
    VerificationStatus.AUTHENTIC_VALID: (
        "Authentic and currently valid. The certificate matches the record registered by an "
        "authorised issuer and has not been revoked."
    ),
    VerificationStatus.REVOKED: (
        "This certificate was issued but has since been revoked. It is NOT currently valid."
    ),
    VerificationStatus.UNKNOWN: "No record of this certificate exists on the blockchain.",
    VerificationStatus.COMMITMENT_MISMATCH: (
        "A certificate with this ID is registered, but the data supplied does not match it. "
        "The document may have been altered, or the wrong file was supplied."
    ),
    VerificationStatus.INVALID_ISSUER: (
        "The account that registered this certificate is no longer an authorised issuer. "
        "Treat the certificate as unverified."
    ),
    VerificationStatus.SERVICE_UNAVAILABLE: (
        "The verification service could not reach the blockchain, so no conclusion can be drawn. "
        "Please try again later."
    ),
}


def _iso(unix_seconds: int) -> str:
    return datetime.fromtimestamp(unix_seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _result(
    status: VerificationStatus,
    certificate_id: str,
    checks: VerificationChecks,
    issuer: Optional[str] = None,
    issued_at: Optional[int] = None,
) -> VerificationResult:
    return VerificationResult(
        status=status,
        valid=status == VerificationStatus.AUTHENTIC_VALID,
        message=MESSAGES[status],
        note=NOTE,
        certificate_id=certificate_id,
        checks=checks,
        issuer=issuer,
        registered_at=_iso(issued_at) if issued_at else None,
        verified_at=_now(),
    )


def verify_package(chain: ChainClient, package: CertificatePackage) -> VerificationResult:
    cert_id = package.certificate_id
    try:
        commitment = compute_commitment(package.model_dump(), package.salt)
        key = certificate_key(cert_id)
    except CanonicalizationError as exc:
        raise AppError(422, "INVALID_INPUT", str(exc)) from exc

    checks = VerificationChecks()
    try:
        record = chain.get(key)
        if not record.exists:
            checks.registered = False
            return _result(VerificationStatus.UNKNOWN, cert_id, checks)
        checks.registered = True

        if not commitments_equal(commitment, record.commitment):
            checks.commitment_matches = False
            return _result(
                VerificationStatus.COMMITMENT_MISMATCH, cert_id, checks, record.issuer, record.issued_at
            )
        checks.commitment_matches = True

        checks.issuer_authorized = chain.is_authorized_issuer(record.issuer)
    except ChainUnavailableError:
        return _result(VerificationStatus.SERVICE_UNAVAILABLE, cert_id, VerificationChecks())

    checks.not_revoked = not record.revoked
    if record.revoked:
        status = VerificationStatus.REVOKED
    elif not checks.issuer_authorized:
        status = VerificationStatus.INVALID_ISSUER
    else:
        status = VerificationStatus.AUTHENTIC_VALID
    return _result(status, cert_id, checks, record.issuer, record.issued_at)


def lookup_status(chain: ChainClient, certificate_id: str) -> StatusLookupResult:
    """QR-code lookup: is there an active record for this ID? (No contents are checked.)"""
    key = certificate_key(certificate_id)
    try:
        record = chain.get(key)
        if not record.exists:
            return StatusLookupResult(
                certificate_id=certificate_id,
                status="UNKNOWN",
                message="No record of this certificate ID exists on the blockchain.",
            )
        authorized = chain.is_authorized_issuer(record.issuer)
    except ChainUnavailableError:
        return StatusLookupResult(
            certificate_id=certificate_id,
            status="SERVICE_UNAVAILABLE",
            message=MESSAGES[VerificationStatus.SERVICE_UNAVAILABLE],
        )

    if record.revoked:
        status, message = "REVOKED", "This certificate has been revoked and is NOT currently valid."
    elif not authorized:
        status, message = "INVALID_ISSUER", MESSAGES[VerificationStatus.INVALID_ISSUER]
    else:
        status = "REGISTERED"
        message = (
            "A record exists and is currently active. This lookup does NOT check the certificate "
            "contents: use full verification with the certificate file to confirm it is authentic."
        )
    return StatusLookupResult(
        certificate_id=certificate_id,
        status=status,
        message=message,
        issuer=record.issuer,
        registered_at=_iso(record.issued_at),
    )