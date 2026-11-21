from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utcnow


class CertificateStatus:
    PENDING = "PENDING"        # saved in the database, not yet confirmed on the blockchain
    REGISTERED = "REGISTERED"  # commitment confirmed on the blockchain
    REVOKED = "REVOKED"        # revoked on the blockchain
    FAILED = "FAILED"          # blockchain registration failed (can be retried)


class Certificate(Base):
    """Private application record. Personal data lives here, never on the blockchain."""

    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    certificate_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    student_id: Mapped[str] = mapped_column(String(40), index=True)
    student_name: Mapped[str] = mapped_column(String(120))
    institution_name: Mapped[str] = mapped_column(String(160))
    degree: Mapped[str] = mapped_column(String(160))
    department: Mapped[str] = mapped_column(String(160))
    graduation_year: Mapped[int] = mapped_column(Integer)

    salt: Mapped[str] = mapped_column(String(64))
    commitment: Mapped[str] = mapped_column(String(66))
    chain_key: Mapped[str] = mapped_column(String(66))
    access_code_hash: Mapped[str] = mapped_column(String(64))

    status: Mapped[str] = mapped_column(String(16), default=CertificateStatus.PENDING, index=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    revoke_tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    issuer_address: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)