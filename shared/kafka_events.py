from datetime import datetime, timezone

RESEARCH_CREATED = "research.created"
RESEARCH_PLANNED = "research.planned"
RESEARCH_SEARCHED = "research.search.completed"
RESEARCH_SUMMARIZED = "research.summary.completed"
RESEARCH_CRITIQUED = "research.critique.completed"
RESEARCH_COMPLETED = "research.completed"
RESEARCH_FAILED = "research.failed"
AGENT_LOGS = "agent.logs"

ALL_PROGRESS_TOPICS = [
    RESEARCH_PLANNED,
    RESEARCH_SEARCHED,
    RESEARCH_SUMMARIZED,
    RESEARCH_CRITIQUED,
    RESEARCH_COMPLETED,
    RESEARCH_FAILED,
]


def make_event(task_id: str, event: str, service: str, payload: dict | None = None) -> dict:
    return {
        "task_id": task_id,
        "event": event,
        "service": service,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
