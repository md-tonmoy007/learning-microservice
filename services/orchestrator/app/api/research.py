from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.research import TaskDetailResponse, TaskStatusResponse
from app.services.research import get_task

router = APIRouter()


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
