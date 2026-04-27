from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.research import (
    CreateResearchRequest,
    ResearchResponse,
    TaskDetailResponse,
    TaskStatusResponse,
)
from app.services.research import create_task, get_task, run_workflow

router = APIRouter()


@router.post("", response_model=ResearchResponse, status_code=202)
async def create_research(
    request: CreateResearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task = await create_task(db, request.query)
    # Note: run_workflow creates its own session — do not pass db here
    background_tasks.add_task(run_workflow, task.id, request.query)
    return ResearchResponse(
        task_id=task.id,
        status=task.status,
        message=f"Research started. Poll /internal/research/{task.id}/status for updates.",
    )


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_research(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetailResponse(
        task_id=task.id,
        query=task.user_query,
        status=task.status,
        final_report=task.final_report,
        iteration_count=task.iteration_count,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_status(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(task_id=task.id, status=task.status)
