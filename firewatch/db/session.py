"""Database engine and sessions.

Uses DATABASE_URL (Supabase PostgreSQL) when it is set in secrets or the
environment, and falls back to a local SQLite file for development (SRS 2.4).
Works both inside Streamlit and in plain scripts.
"""
import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from firewatch.db.models import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = PROJECT_ROOT / "data" / "firewatch.db"


def get_secret(name: str, default=None):
    """Reads from .streamlit/secrets.toml (via st.secrets), then environment variables."""
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, default)


def _normalize(url: str) -> str:
    # Supabase shows postgresql:// (or postgres://); SQLAlchemy needs the driver name.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


@lru_cache(maxsize=1)
def get_engine():
    """Created once per process. Streamlit reruns the script on every click,
    but imported modules (and this cache) persist, so connections are reused."""
    url = get_secret("DATABASE_URL")
    if url:
        engine = create_engine(_normalize(url), pool_pre_ping=True,
                               pool_size=3, max_overflow=2, pool_recycle=1800)
    else:
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{SQLITE_PATH}",
                               connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _):        # SQLite ignores foreign keys unless asked
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)          # creates any missing tables
    return engine


@lru_cache(maxsize=1)
def _factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope():
    """Usage:  with session_scope() as db: db.add(...)
    Commits on success, rolls back on any error, always closes."""
    db = _factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def backend_name() -> str:
    return get_engine().dialect.name          # "postgresql" or "sqlite"