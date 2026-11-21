"""Password hashing, JWT tokens, student access codes and a tiny rate limiter."""
import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("ascii"))
    except ValueError:
        return False


# A real bcrypt hash used so that unknown usernames cost the same time as known ones.
DUMMY_HASH = hash_password("not-a-real-password")


# --------------------------------------------------------------------- JWT
def create_access_token(subject: str, role: str = "admin") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError if the token is invalid or expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])


# ------------------------------------------------------ student access codes
def generate_access_code() -> str:
    return secrets.token_urlsafe(9)  # 12 URL-safe characters, ~72 bits of randomness


def hash_access_code(code: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_access_code(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_access_code(code), code_hash)


# ------------------------------------------------------------ rate limiting
class RateLimiter:
    """In-memory failed-attempt limiter (single process; fine for a demo)."""

    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str) -> list[float]:
        cutoff = time.monotonic() - self.window
        recent = [t for t in self._failures.get(key, []) if t > cutoff]
        self._failures[key] = recent
        return recent

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._recent(key)) >= self.max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._recent(key).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = RateLimiter(max_failures=5, window_seconds=300)
student_limiter = RateLimiter(max_failures=5, window_seconds=300)