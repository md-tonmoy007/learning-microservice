from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.research import router
from app.core.config import settings
from app.core.kafka import start_producer, stop_producer
from app.core.redis_client import start_redis, stop_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer(settings.kafka_bootstrap_servers)
    await start_redis(settings.redis_url)
    yield
    await stop_producer()
    await stop_redis()


app = FastAPI(title="API Gateway", version="0.1.0", lifespan=lifespan)

app.include_router(router, prefix="/research", tags=["research"])


@app.get("/health")
async def health():
    return {"status": "ok"}
