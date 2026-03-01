# engine.py
from __future__ import annotations

import os
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    repo_root = Path(__file__).resolve().parents[3]
    db_path = repo_root / ".local" / "bayesiq_dev.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"

_ENGINE = create_engine(get_database_url(), future=True, echo=False, connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(
    bind=_ENGINE,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)

def engine():
    return _ENGINE

@contextmanager
def db_session() -> Session:
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()          # ✅ single source of truth
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()