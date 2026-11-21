from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.crypto.canonical import SCHEMA_VERSION, normalize_text
from app.schemas.common import UtcDatetime
from app.utils.validators import CERT_ID_PATTERN, SALT_PATTERN, STUDENT_ID_PATTERN, has_control_chars


class CertificateCreate(BaseModel):
    """Data the administrator types in when issuing a certificate."""

    model_config = ConfigDict(str_strip_whitespace=True)

    certificate_id: str = Field(pattern=CERT_ID_PATTERN, examples=["CERT-2026-0001"])
    student_name: str = Field(min_length=1, max_length=120)
    student_id: str = Field(pattern=STUDENT_ID_PATTERN, examples=["STU1001"])
    institution_name: str = Field(min_length=1, max_length=160)
    degree: str = Field(min_length=1, max_length=160)
    department: str = Field(min_length=1, max_length=160)
    graduation_year: int = Field(ge=1950, le=2100)

    @field_validator("student_name", "institution_name", "degree", "department")
    @classmethod
    def _clean_text(cls, value: str) -> str:
        if has_control_chars(value):
            raise ValueError("control or invisible characters are not allowed")
        value = normalize_text(value)
        if not value:
            raise ValueError("must not be empty")
        return value


class CertificatePackage(BaseModel):
    """The certificate file handed to the student and later shown to a verifier.

    Used both as the downloadable file and as the verification request body.
    Validation is deliberately lenient (length caps only): a tampered certificate
    must reach the verifier and fail as COMMITMENT_MISMATCH, not be bounced as bad input.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = Field(default=SCHEMA_VERSION, alias="schema")
    certificate_id: str = Field(min_length=1, max_length=64)
    student_name: str = Field(min_length=1, max_length=120)
    student_id: str = Field(min_length=1, max_length=40)
    institution_name: str = Field(min_length=1, max_length=160)
    degree: str = Field(min_length=1, max_length=160)
    department: str = Field(min_length=1, max_length=160)
    graduation_year: int = Field(ge=0, le=9999)
    salt: str = Field(pattern=SALT_PATTERN)

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema, expected '{SCHEMA_VERSION}'")
        return value


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    certificate_id: str
    student_id: str
    student_name: str
    institution_name: str
    degree: str
    department: str
    graduation_year: int
    commitment: str
    status: str
    tx_hash: Optional[str] = None
    revoke_tx_hash: Optional[str] = None
    issuer_address: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: UtcDatetime
    registered_at: Optional[UtcDatetime] = None
    revoked_at: Optional[UtcDatetime] = None


class CertificateListResponse(BaseModel):
    items: list[CertificateOut]
    total: int


class IssueResponse(BaseModel):
    certificate: CertificateOut
    access_code: str = Field(description="Shown once. Give it to the student.")
    package: CertificatePackage
    verify_url: str