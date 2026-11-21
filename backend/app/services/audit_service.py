"""Audit trail: who did what, with what outcome. No personal data is stored here."""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_event(
    db: Session,
    event_type: str,
    outcome: str,
    actor: str,
    certificate_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type[:32],
        outcome=outcome[:48],
        actor=actor[:64],
        certificate_id=certificate_id[:64] if certificate_id else None,
        detail=detail[:255] if detail else None,
    )
    db.add(entry)
    db.commit()
    return entry


def list_events(
    db: Session, event_type: Optional[str] = None, limit: int = 50, offset: int = 0
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
        count_query = count_query.where(AuditLog.event_type == event_type)
    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    ).all()
    return list(items), total