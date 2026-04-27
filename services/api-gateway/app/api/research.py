import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.research import (
    ResearchRequest,
    ResearchResponse,
    TaskDetailResponse,
    TaskStatusResponse,
)

router = APIRouter()


@router.post("", response_model=ResearchResponse, status_code=202)
async def submit_research(request: ResearchRequest):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.orchestrator_url}/internal/research",
                json={"query": request.query},
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Orchestrator error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Orchestrator unreachable: {e}")
    return resp.json()


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_research(task_id: str):
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
            raise HTTPException(
                status_code=502, detail=f"Orchestrator error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Orchestrator unreachable: {e}")
    return resp.json()


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_research_status(task_id: str):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{settings.orchestrator_url}/internal/research/{task_id}/status",
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Task not found")
            raise HTTPException(
                status_code=502, detail=f"Orchestrator error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Orchestrator unreachable: {e}")
    return resp.json()
