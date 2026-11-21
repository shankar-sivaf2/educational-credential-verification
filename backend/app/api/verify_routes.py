"""Public verification endpoints (no login: employers are not account holders)."""
from fastapi import APIRouter, Depends, File, Path, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_chain
from app.blockchain.contract_service import ChainClient
from app.core.database import get_db
from app.schemas.certificate import CertificatePackage
from app.schemas.verification import StatusLookupResult, VerificationResult
from app.services import audit_service, verification_service
from app.utils.exceptions import AppError
from app.utils.file_utils import read_json_upload

router = APIRouter(prefix="/verify", tags=["verification"])


def _verify_and_audit(db: Session, chain: ChainClient, package: CertificatePackage) -> VerificationResult:
    result = verification_service.verify_package(chain, package)
    audit_service.log_event(db, "VERIFY", result.status.value, "anonymous", package.certificate_id)
    return result


@router.post("", response_model=VerificationResult)
def verify_certificate(
    package: CertificatePackage,
    db: Session = Depends(get_db),
    chain: ChainClient = Depends(get_chain),
):
    """Submit the certificate data (the JSON file the student downloaded)."""
    return _verify_and_audit(db, chain, package)


@router.post("/upload", response_model=VerificationResult)
def verify_certificate_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    chain: ChainClient = Depends(get_chain),
):
    """Upload the certificate JSON file. It is read in memory and never stored."""
    raw = read_json_upload(file)
    try:
        package = CertificatePackage.model_validate(raw)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:5]
        )
        raise AppError(422, "INVALID_CERTIFICATE_FILE", f"Not a valid certificate file ({problems}).") from exc
    return _verify_and_audit(db, chain, package)


@router.get("/status/{certificate_id}", response_model=StatusLookupResult)
def certificate_status(
    certificate_id: str = Path(min_length=1, max_length=64),
    db: Session = Depends(get_db),
    chain: ChainClient = Depends(get_chain),
):
    """Target of the QR code: current status by ID only. Returns no personal data."""
    result = verification_service.lookup_status(chain, certificate_id)
    audit_service.log_event(db, "STATUS_LOOKUP", result.status, "anonymous", certificate_id)
    return result