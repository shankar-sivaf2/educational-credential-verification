"""Student access: a student sees only their own certificates, using the access code
the institution gave them when the certificate was issued."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import student_limiter
from app.schemas.certificate import CertificateOut, CertificatePackage
from app.schemas.verification import StudentRecord, StudentRecordsRequest, StudentRecordsResponse
from app.services import audit_service, certificate_service
from app.utils.exceptions import AppError

router = APIRouter(prefix="/student", tags=["student"])


@router.post("/records", response_model=StudentRecordsResponse)
def student_records(body: StudentRecordsRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{body.student_id.lower()}"
    if student_limiter.is_blocked(limiter_key):
        raise AppError(429, "TOO_MANY_ATTEMPTS", "Too many failed attempts. Try again in a few minutes.")

    rows = certificate_service.student_records(db, body.student_id, body.access_code)
    if not rows:
        student_limiter.record_failure(limiter_key)
        audit_service.log_event(db, "STUDENT_ACCESS", "FAILED", "student")
        # Same message for "unknown student" and "wrong code", so IDs cannot be probed.
        raise AppError(404, "NO_RECORDS", "No records found for that student ID and access code.")

    student_limiter.reset(limiter_key)
    audit_service.log_event(db, "STUDENT_ACCESS", "SUCCESS", "student", detail=f"{len(rows)} record(s)")
    return StudentRecordsResponse(
        records=[
            StudentRecord(
                certificate=CertificateOut.model_validate(r),
                package=CertificatePackage.model_validate(certificate_service.build_package(r)),
                verify_url=certificate_service.verify_url(r.certificate_id),
            )
            for r in rows
        ]
    )