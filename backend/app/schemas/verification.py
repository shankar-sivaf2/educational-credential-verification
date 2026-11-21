from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.certificate import CertificateOut, CertificatePackage


class VerificationStatus(str, Enum):
    AUTHENTIC_VALID = "AUTHENTIC_VALID"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"
    COMMITMENT_MISMATCH = "COMMITMENT_MISMATCH"
    INVALID_ISSUER = "INVALID_ISSUER"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class VerificationChecks(BaseModel):
    """True = passed, False = failed, None = not checked (an earlier check already failed)."""

    registered: Optional[bool] = None
    commitment_matches: Optional[bool] = None
    issuer_authorized: Optional[bool] = None
    not_revoked: Optional[bool] = None


class VerificationResult(BaseModel):
    status: VerificationStatus
    valid: bool
    message: str
    note: str
    certificate_id: str
    checks: VerificationChecks
    issuer: Optional[str] = None
    registered_at: Optional[str] = None
    verified_at: str


class StatusLookupResult(BaseModel):
    """Result of a QR-code lookup. Contains no personal data and does NOT check certificate contents."""

    certificate_id: str
    status: str  # REGISTERED | REVOKED | INVALID_ISSUER | UNKNOWN | SERVICE_UNAVAILABLE
    message: str
    issuer: Optional[str] = None
    registered_at: Optional[str] = None


class StudentRecordsRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=40)
    access_code: str = Field(min_length=1, max_length=64)


class StudentRecord(BaseModel):
    certificate: CertificateOut
    package: CertificatePackage
    verify_url: str


class StudentRecordsResponse(BaseModel):
    records: list[StudentRecord]