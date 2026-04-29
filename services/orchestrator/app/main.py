import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.research import router
from app.core.config import settings
from app.core.database import engine
from app.core.kafka import run_research_consumer, start_producer, stop_producer
from app.core.redis_client import start_redis, stop_redis
from app.models import research  # noqa: F401 — registers models with Base for Alembic
from app.services.research import run_workflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer(settings.kafka_bootstrap_servers)
    await start_redis(settings.redis_url)
    consumer_task = asyncio.create_task(
        run_research_consumer(settings.kafka_bootstrap_servers, run_workflow)
    )
    yield
    consumer_task.cancel()
    await asyncio.gather(consumer_task, return_exceptions=True)
    await stop_producer()
    await stop_redis()
    await engine.dispose()


app = FastAPI(title="Orchestrator", version="0.1.0", lifespan=lifespan)

app.include_router(router, prefix="/internal/research", tags=["internal"])


@app.get("/health")
async def health():
    return {"status": "ok"}
