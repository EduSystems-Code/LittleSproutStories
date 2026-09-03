import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 - registers every model on Base.metadata before create_all runs
from app.api.routes import admin, board, checkout, health, requests_, webhooks
from app.config import get_settings
from app.db.base import Base
from app.db.session import engine

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Alembic owns schema changes going forward; this is a safety net so a
    # fresh clone works even before the first `alembic upgrade head`.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Little Sprout Rewards", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,  # admin session cookie needs this
)

app.include_router(health.router, prefix="/api")
app.include_router(checkout.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(requests_.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(board.router, prefix="/api")
