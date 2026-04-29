import asyncio
import json
from uuid import uuid4

import httpx
from aiokafka import AIOKafkaConsumer
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.kafka import publish_event
from app.core.redis_client import get_redis
from app.schemas.research import ResearchRequest, ResearchResponse, TaskDetailResponse, TaskStatusResponse
from shared.kafka_events import (
    ALL_PROGRESS_TOPICS,
    RESEARCH_COMPLETED,
    RESEARCH_CREATED,
    RESEARCH_FAILED,
    make_event,
)

router = APIRouter()


@router.post("", response_model=ResearchResponse, status_code=202)
async def submit_research(request: ResearchRequest):
    task_id = str(uuid4())
    event = make_event(task_id, RESEARCH_CREATED, "api-gateway", {"query": request.query})
    await publish_event(RESEARCH_CREATED, event)
    return ResearchResponse(
        task_id=task_id,
        status="pending",
        message=f"Research queued. Stream progress at /research/{task_id}/events",
    )


@router.get("/{task_id}/events")
async def stream_events(task_id: str, request: Request):
    """SSE stream of real-time workflow progress for a given task."""

    async def generator():
        consumer = AIOKafkaConsumer(
            *ALL_PROGRESS_TOPICS,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=f"gateway-sse-{task_id}-{uuid4().hex}",
            auto_offset_reset="earliest",
        )
        await consumer.start()
        try:
            async for msg in consumer:
                if await request.is_disconnected():
                    break
                event = json.loads(msg.value)
                if event["task_id"] == task_id:
                    yield f"data: {json.dumps(event)}\n\n"
                    if event["event"] in (RESEARCH_COMPLETED, RESEARCH_FAILED):
                        break
        finally:
            await consumer.stop()

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_research_status(task_id: str):
    """Fast status lookup from Redis — no DB round-trip."""
    redis = get_redis()
    raw = await redis.get(f"task:{task_id}:status")
    if raw is None:
        raise HTTPException(status_code=404, detail="Task not found")
    data = json.loads(raw)
    return TaskStatusResponse(task_id=task_id, status=data["status"])


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_research(task_id: str):
    """Full task detail — proxied to orchestrator (includes final report)."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{settings.orchestrator_url}/internal/research/{task_id}",
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Task not found")
            raise HTTPException(status_code=502, detail=f"Orchestrator error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Orchestrator unreachable: {e}")
    return resp.json()
