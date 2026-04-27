from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.research import router
from app.core.database import engine
from app.models import research  # noqa: F401 — registers models with Base for Alembic


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Orchestrator", version="0.1.0", lifespan=lifespan)

app.include_router(router, prefix="/internal/research", tags=["internal"])


@app.get("/health")
async def health():
    return {"status": "ok"}
