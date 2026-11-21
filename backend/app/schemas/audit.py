from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    outcome: str
    actor: str
    certificate_id: Optional[str] = None
    detail: Optional[str] = None
    created_at: UtcDatetime


class AuditListResponse(BaseModel):
    items: list[AuditOut]
    total: int