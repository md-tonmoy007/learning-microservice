from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.research import router
from app.core.config import settings
from app.core.kafka import start_producer, stop_producer
from app.core.redis_client import start_redis, stop_redis
from app.core.telemetry import setup_telemetry

setup_telemetry("api-gateway", settings.otel_endpoint)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer(settings.kafka_bootstrap_servers)
    await start_redis(settings.redis_url)
    yield
    await stop_producer()
    await stop_redis()


app = FastAPI(title="API Gateway", version="0.1.0", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)

app.include_router(router, prefix="/research", tags=["research"])


@app.get("/health")
async def health():
    return {"status": "ok"}
