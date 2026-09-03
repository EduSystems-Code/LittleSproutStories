"""Settings.sqlalchemy_url -- the DATABASE_URL driver normalisation that
lets the same code run on local SQLite and deployed Postgres."""
import pytest

from app.config import Settings


@pytest.mark.parametrize(
    "raw, expected",
    [
        # bare postgres:// (what some managed providers hand back) -> psycopg v3
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        # bare postgresql:// (SQLAlchemy would default this to psycopg2) -> psycopg v3
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        # already names a driver -> untouched
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg2://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),
        # sqlite -> untouched
        ("sqlite:///./data/rewards.db", "sqlite:///./data/rewards.db"),
        ("sqlite:///:memory:", "sqlite:///:memory:"),
    ],
)
def test_sqlalchemy_url_normalisation(raw, expected):
    assert Settings(database_url=raw).sqlalchemy_url == expected


def test_default_is_sqlite():
    assert Settings().sqlalchemy_url.startswith("sqlite:///")
