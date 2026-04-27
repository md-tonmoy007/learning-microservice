from datetime import datetime

from pydantic import BaseModel


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str


class TaskDetailResponse(BaseModel):
    task_id: str
    query: str
    status: str
    final_report: str | None = None
    iteration_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
