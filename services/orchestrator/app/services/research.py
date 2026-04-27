import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.graph.state import ResearchState
from app.graph.workflow import research_graph
from app.models.research import ResearchTask


async def create_task(db: AsyncSession, query: str) -> ResearchTask:
    task = ResearchTask(user_query=query, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: str) -> ResearchTask | None:
    result = await db.execute(
        select(ResearchTask).where(ResearchTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def run_workflow(task_id: str, query: str) -> None:
    """Run the full LangGraph research workflow.

    Creates its own DB session — the HTTP request's session will be closed
    by the time this background task runs.
    """
    async with AsyncSessionFactory() as db:
        task = await get_task(db, task_id)
        if not task:
            return

        task.status = "running"
        await db.commit()

        initial_state: ResearchState = {
            "task_id": task_id,
            "user_query": query,
            "research_plan": [],
            "search_results": [],
            "summaries": [],
            "critique": {},
            "final_report": "",
            "iteration_count": 0,
            "status": "running",
        }

        try:
            final_state = await research_graph.ainvoke(initial_state)
            task.status = final_state.get("status", "completed")
            task.final_report = final_state.get("final_report", "")
            task.iteration_count = final_state.get("iteration_count", 0)
            task.research_plan = json.dumps(final_state.get("research_plan", []))
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)

        await db.commit()
