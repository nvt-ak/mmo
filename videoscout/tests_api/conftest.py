"""Test fixtures: in-memory SQLite database + test client."""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

# Must be set BEFORE any app.db import
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy.types as types

from videoscout.db.models import Base

# JSONB → JSON for SQLite
for _tbl in Base.metadata.tables.values():
    for _col in _tbl.columns:
        if isinstance(_col.type, JSONB):
            _col.type = types.JSON()

# Stub init_db globally before app.main imports it
import videoscout.db as _dbmod
_dbmod._init_db_called = False
_orig_init_db = _dbmod.init_db

def _stub_init_db(database_url=None):
    if not _dbmod._init_db_called:
        _dbmod._init_db_called = True
        # Create in-memory SQLite engine for the app
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        _dbmod._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_dbmod.init_db = _stub_init_db


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client(db_session):
    from videoscout.db import get_db
    from videoscout.api_main import app

    app.dependency_overrides[get_db] = lambda: (yield db_session)

    # Background tasks (scan) use get_session() — redirect to test session
    import videoscout.db as _dbmod
    _dbmod.get_session = lambda: db_session

    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_suggestion(db_session):
    from videoscout.db.models import SuggestionModel

    s = SuggestionModel(
        keyword="ai marketing for small business",
        final_score=0.78,
        component_scores={
            "relevance": 0.90, "specificity": 0.85,
            "saturation": 0.70, "trend": 0.50, "video_performance": 0.75
        },
        suggested_by=[{
            "source": "digest_scan", "video_id": "vid_001",
            "channel_id": "UC_test_001", "score": 0.78,
            "timestamp": "2026-07-01T05:00:00"
        }],
        tiktok_status="moderate",
        tiktok_count_at_suggest=15,
        status="pending",
        keyword_type="beta",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s
