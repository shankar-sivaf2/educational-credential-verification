from typing import Optional
from fastapi import APIRouter, Depends, Query, Response

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_chain, get_current_admin
from app.blockchain.contract_service import ChainClient
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.certificate import (
    CertificateCreate,
    CertificateListResponse,
    CertificateOut,
    CertificatePackage,
    IssueResponse,
)
from app.services import certificate_service, qr_service

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post("", response_model=IssueResponse, status_code=201)
def issue_certificate(
    payload: CertificateCreate,
    db: Session = Depends(get_db),
    chain: ChainClient = Depends(get_chain),
    admin: AdminUser = Depends(get_current_admin),
):
    row, access_code = certificate_service.issue_certificate(db, chain, payload, admin.username)
    return IssueResponse(
        certificate=CertificateOut.model_validate(row),
        access_code=access_code,
        package=CertificatePackage.model_validate(certificate_service.build_package(row)),
        verify_url=certificate_service.verify_url(row.certificate_id),
    )


@router.get("", response_model=CertificateListResponse)
def list_certificates(
    status: Optional[str] = Query(default=None, pattern="^(PENDING|REGISTERED|REVOKED|FAILED)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    items, total = certificate_service.list_certificates(db, status, limit, offset)
    return CertificateListResponse(
        items=[CertificateOut.model_validate(r) for r in items], total=total
    )


@router.get("/{certificate_id}", response_model=CertificateOut)
def get_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return certificate_service.get_certificate(db, certificate_id)


@router.post("/{certificate_id}/revoke", response_model=CertificateOut)
def revoke_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
    chain: ChainClient = Depends(get_chain),
    admin: AdminUser = Depends(get_current_admin),
):
    return certificate_service.revoke_certificate(db, chain, certificate_id, admin.username)


@router.get("/{certificate_id}/qr.png")
def certificate_qr(
    certificate_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """PNG QR code pointing at the public verification page. Contains no personal data."""
    row = certificate_service.get_certificate(db, certificate_id)
    png = qr_service.make_qr_png(certificate_service.verify_url(row.certificate_id))
    return Response(content=png, media_type="image/png")