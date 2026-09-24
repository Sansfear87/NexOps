from typing import Generator
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings


def get_sync_database_url() -> str:
    """Normalize configured database URL for synchronous SQLAlchemy driver."""
    url = os.getenv("SYNC_DATABASE_URL") or getattr(settings, "SYNC_DATABASE_URL", None)
    if not url:
        raw_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
        if "sqlite" in raw_url:
            url = raw_url.replace("+aiosqlite", "")
        elif "+asyncpg" in raw_url:
            url = raw_url.replace("+asyncpg", "+psycopg2")
        elif raw_url.startswith("postgresql://"):
            url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        else:
            url = raw_url
    return url


DATABASE_URL = get_sync_database_url()

# Configure engine kwargs
engine_kwargs = {"echo": settings.DEBUG}
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Ensure foreign key constraints are enforced on SQLite
if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
