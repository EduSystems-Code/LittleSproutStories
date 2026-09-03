"""Shared fixtures. Every test runs against a fresh in-memory SQLite DB
(never the real data/rewards.db file) via a get_db dependency override --
tests must never write into, or silently depend on, real data."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers every model on Base.metadata
from app.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.order import Order


TEST_ADMIN_PASSWORD = "test-admin-password"


@pytest.fixture
def db_engine():
    # StaticPool: plain sqlite:///:memory: hands out a FRESH, empty
    # in-memory database on every new connection (a well-known SQLAlchemy
    # gotcha) -- StaticPool forces the whole engine to reuse one single
    # connection, so the tables created below are actually still there
    # when a later query opens "a new connection" through the same engine.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine, monkeypatch):
    TestingSessionLocal = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # get_settings() is @lru_cache'd and called DIRECTLY throughout the app
    # (not via FastAPI's Depends() -- matching Chegga's own config.py
    # pattern), so a dependency_overrides entry would never intercept it.
    # Set real env vars and clear the cache instead, which affects every
    # direct call the same way a real deployment's .env would.
    monkeypatch.setenv("ADMIN_PASSWORD", TEST_ADMIN_PASSWORD)
    monkeypatch.setenv("ADMIN_COOKIE_SECURE", "false")  # TestClient has no real https
    get_settings.cache_clear()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def make_paid_order(db: Session, stripe_checkout_session_id: str = "cs_test", amount_cents: int = 1000, product_id: str = "reward_box") -> Order:
    order = Order(
        stripe_checkout_session_id=stripe_checkout_session_id,
        amount_cents=amount_cents,
        product_id=product_id,
        paid=True,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
