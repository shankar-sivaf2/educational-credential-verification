"""Shared FastAPI dependencies."""
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blockchain.contract_service import ChainClient
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.admin_user import AdminUser
from app.utils.exceptions import AppError

bearer_scheme = HTTPBearer(auto_error=False)


def get_chain(request: Request) -> ChainClient:
    chain = getattr(request.app.state, "chain", None)
    if chain is None:
        raise AppError(503, "BLOCKCHAIN_UNAVAILABLE", "Blockchain client is not initialised.")
    return chain


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    if credentials is None:
        raise AppError(401, "NOT_AUTHENTICATED", "Administrator login required.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise AppError(401, "INVALID_TOKEN", "Your session is invalid or has expired. Please log in again.")
    if payload.get("role") != "admin":
        raise AppError(403, "FORBIDDEN", "Administrator role required.")
    user = db.scalar(select(AdminUser).where(AdminUser.username == payload.get("sub")))
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "Account no longer exists.")
    return user