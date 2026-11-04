"""Database session configuration and connectivity utilities."""

import time
from typing import Generator, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Create SQLAlchemy engine with connection pooling and pre-ping validation
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args={"connect_timeout": int(settings.DB_CONNECT_TIMEOUT)},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency generator that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connectivity() -> Tuple[bool, Optional[float], Optional[str]]:
    """Perform a lightweight database connectivity check.
    
    Returns:
        Tuple of (is_connected, latency_ms, error_message)
    """
    start_time = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return True, latency_ms, None
    except SQLAlchemyError as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, latency_ms, str(exc.orig if hasattr(exc, "orig") else exc)
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, latency_ms, str(exc)

