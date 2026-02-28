from __future__ import annotations

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

def get_database_url() -> str:
    # SQLite-first default (no Docker needed)
    return os.getenv("DATABASE_URL", "sqlite:///./bayesiq_dev.db")

def make_engine():
    url = get_database_url()

    # SQLite needs this flag for multithreaded use; harmless otherwise
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, echo=False, connect_args=connect_args)

_ENGINE = make_engine()
_SessionLocal = sessionmaker(
    bind=_ENGINE,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,   # ✅ add this
)

def engine():
    return _ENGINE

@contextmanager
def db_session() -> Session:
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()