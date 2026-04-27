---
tags: [home, index]
---

# Multi-Agent Research Assistant — Tutorial Home

> Personal learning notes for the microservices + multi-agent orchestration project.

---

## Phases

| Phase | Topic                              | Status   |
|------|------------------------------------|----------|
| 1    | [[API Gateway]] · [[LangGraph Orchestrator]] · [[ResearchState]] · [[PostgreSQL Models]] | In progress |
| 2    | gRPC Agent Decomposition           | Not started |
| 3    | Kafka/Redpanda + Redis + SSE       | Not started |
| 4    | Prometheus + Grafana + Loki + OTEL | Not started |
| 5    | Qdrant Vector Memory               | Not started |
| 6    | Kubernetes + Helm + CI/CD          | Not started |

---

## Phase 1 Notes

- [[API Gateway]] — FastAPI entry point, httpx proxy to orchestrator
- [[LangGraph Orchestrator]] — LangGraph workflow, BackgroundTasks, full run loop
- [[ResearchState]] — TypedDict state, how it flows between nodes
- [[PostgreSQL Models]] — SQLAlchemy async, Alembic, ResearchTask model

---

## Concept Notes

- [[LangGraph Concepts]] — StateGraph, nodes, edges, conditional routing
- [[FastAPI Background Tasks]] — how BackgroundTasks works, the session lifecycle gotcha
- [[SQLAlchemy Async]] — engine, async_sessionmaker, Mapped columns, get_db

---

## Debugging Notes

_(none yet — add a note here every time something breaks)_

---

## How to Use These Notes

- Every main note has a `file:` frontmatter pointing to the source file it documents.
- Use `[[Wikilinks]]` to jump between notes — never plain markdown links between notes.
- When you hit an error: fix it, then write a `[[debugging/Error Name]]` note before moving on.
