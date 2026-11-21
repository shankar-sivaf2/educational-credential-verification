from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.core.security import create_access_token, login_limiter
from app.models.admin_user import AdminUser
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse
from app.services import audit_service, auth_service
from app.utils.exceptions import AppError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{body.username.lower()}"
    if login_limiter.is_blocked(limiter_key):
        raise AppError(429, "TOO_MANY_ATTEMPTS", "Too many failed logins. Try again in a few minutes.")

    user = auth_service.authenticate(db, body.username, body.password)
    if user is None:
        login_limiter.record_failure(limiter_key)
        audit_service.log_event(db, "LOGIN", "FAILED", body.username[:64])
        raise AppError(401, "INVALID_CREDENTIALS", "Incorrect username or password.")

    login_limiter.reset(limiter_key)
    audit_service.log_event(db, "LOGIN", "SUCCESS", user.username)
    return TokenResponse(access_token=create_access_token(user.username), username=user.username)


@router.get("/me", response_model=MeResponse)
def me(admin: AdminUser = Depends(get_current_admin)):
    return MeResponse(username=admin.username)