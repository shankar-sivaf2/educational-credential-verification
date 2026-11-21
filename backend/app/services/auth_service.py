"""Administrator accounts and login."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import DUMMY_HASH, hash_password, verify_password
from app.models.admin_user import AdminUser


def ensure_admin(db: Session, username: str, password: str) -> AdminUser:
    """Create the administrator on first start. An existing password is never overwritten."""
    user = db.scalar(select(AdminUser).where(AdminUser.username == username))
    if user is None:
        user = AdminUser(username=username, password_hash=hash_password(password))
        db.add(user)
        db.commit()
    return user


def authenticate(db: Session, username: str, password: str) -> Optional[AdminUser]:
    user = db.scalar(select(AdminUser).where(AdminUser.username == username))
    # Always run one bcrypt check so unknown usernames take as long as wrong passwords.
    ok = verify_password(password, user.password_hash if user else DUMMY_HASH)
    return user if (user and ok) else None