import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.core.kafka import publish_event
from app.core.redis_client import get_redis
from app.graph.state import ResearchState
from app.graph.workflow import research_graph
from app.models.research import ResearchTask
from shared.kafka_events import (
    RESEARCH_COMPLETED,
    RESEARCH_CRITIQUED,
    RESEARCH_FAILED,
    RESEARCH_PLANNED,
    RESEARCH_SEARCHED,
    RESEARCH_SUMMARIZED,
    make_event,
)

logger = logging.getLogger(__name__)

# Maps node name → Kafka topic emitted after that node completes
_NODE_TOPIC: dict[str, str] = {
    "plan_research": RESEARCH_PLANNED,
    "search_web": RESEARCH_SEARCHED,
    "summarize_results": RESEARCH_SUMMARIZED,
    "critique_answer": RESEARCH_CRITIQUED,
}


async def _set_redis_status(task_id: str, status: str) -> None:
    redis = get_redis()
    await redis.set(f"task:{task_id}:status", json.dumps({"status": status}))


async def create_task(db: AsyncSession, query: str) -> ResearchTask:
    task = ResearchTask(user_query=query, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: str) -> ResearchTask | None:
    result = await db.execute(select(ResearchTask).where(ResearchTask.id == task_id))
    return result.scalar_one_or_none()


async def run_workflow(task_id: str, query: str) -> None:
    """Consume a research.created event: persist the task, run LangGraph, emit Kafka events."""
    async with AsyncSessionFactory() as db:
        # Create or find the task record
        task = ResearchTask(id=task_id, user_query=query, status="running")
        db.add(task)
        try:
            await db.commit()
            await db.refresh(task)
        except Exception:
            # Task already exists (duplicate delivery) — load it instead
            await db.rollback()
            task = await get_task(db, task_id)
            if not task:
                logger.error("Task %s not found after insert conflict", task_id)
                return
            task.status = "running"
            await db.commit()

        await _set_redis_status(task_id, "running")

        initial_state: ResearchState = {
            "task_id": task_id,
            "user_query": query,
            "research_plan": [],
            "report_sections": [],
            "search_results": [],
            "summaries": [],
            "critique": {},
            "final_report": "",
            "iteration_count": 0,
            "status": "running",
        }

        current_state = dict(initial_state)

        try:
            async for output in research_graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in output.items():
                    current_state.update(node_output)
                    topic = _NODE_TOPIC.get(node_name)
                    if topic:
                        event = make_event(
                            task_id,
                            topic,
                            "orchestrator",
                            {"status": node_output.get("status", node_name)},
                        )
                        await publish_event(topic, event)
                        await _set_redis_status(task_id, node_output.get("status", node_name))
                        logger.info("Published %s for task %s", topic, task_id)

            task.status = current_state.get("status", "completed")
            task.final_report = current_state.get("final_report", "")
            task.iteration_count = current_state.get("iteration_count", 0)
            task.research_plan = json.dumps(current_state.get("research_plan", []))
            await db.commit()

            await _set_redis_status(task_id, "completed")
            await publish_event(
                RESEARCH_COMPLETED,
                make_event(task_id, RESEARCH_COMPLETED, "orchestrator"),
            )

        except Exception as exc:
            logger.exception("Workflow failed for task %s", task_id)
            task.status = "failed"
            task.error_message = str(exc)
            await db.commit()

            await _set_redis_status(task_id, "failed")
            await publish_event(
                RESEARCH_FAILED,
                make_event(task_id, RESEARCH_FAILED, "orchestrator", {"error": str(exc)}),
            )
