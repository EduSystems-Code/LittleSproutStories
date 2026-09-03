from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

DB_URL = settings.sqlalchemy_url
_IS_SQLITE = DB_URL.startswith("sqlite")

# The sqlite file's parent directory must exist before the engine opens it --
# a fresh clone only has data/.gitkeep tracked, not the db file itself.
if DB_URL.startswith("sqlite:///"):
    db_path = Path(DB_URL.replace("sqlite:///", "", 1))
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if _IS_SQLITE else {},
    # A managed Postgres can drop idle connections; check one is alive
    # before handing it out rather than failing the request.
    pool_pre_ping=not _IS_SQLITE,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
