"""Database initialization and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

# This will be set via environment variables
_engine = None
_SessionLocal = None


def init_db(database_url: str):
    """Initialize database engine and session factory."""
    global _engine, _SessionLocal
    
    _engine = create_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )
    
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Create tables
    Base.metadata.create_all(bind=_engine)


def get_db() -> Session:
    """Dependency for FastAPI to get database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """Standalone session getter (for non-FastAPI code)."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal()
