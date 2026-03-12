"""
SQLAlchemy engine, session factory, and FastAPI dependency.

Uses SQLite as the database backend with WAL mode for
better concurrent read performance.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.config import DATABASE_URL, DATABASE_DIR

logger = logging.getLogger(__name__)

# ── Ensure data directory exists ─────────────────────────────────────
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# ── Engine ───────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=False,
)


# Enable WAL mode for better concurrent reads
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
