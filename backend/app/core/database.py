"""SQLAlchemy engine, session factory and table creation."""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import BACKEND_DIR, settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (SQLite stores no timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def resolve_sqlite_url(url: str) -> str:
    """Make relative sqlite paths relative to backend/ and create the folder."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path = url[len(prefix):]
    if path in ("", ":memory:"):
        return url
    p = Path(path)
    if not p.is_absolute():
        p = (BACKEND_DIR / p).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return f"{prefix}{p.as_posix()}"


def make_engine(url: str):
    url = resolve_sqlite_url(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401  (registers the tables)

    Base.metadata.create_all(bind=engine)