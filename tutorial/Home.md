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
| 2    | [[gRPC Agent Decomposition]] · [[Planner Agent]] · [[Search Agent]] · [[Summarizer Agent]] · [[Critic Agent]] · [[Report Service]] | In progress |
| 3    | Kafka/Redpanda + Redis + SSE       | Not started |
| 4    | Prometheus + Grafana + Loki + OTEL | Not started |
| 5    | Qdrant Vector Memory               | Not started |
| 6    | Kubernetes + Helm + CI/CD          | Not started |

---

## Phase 1 Notes

- [[Project Structure]] — every folder and file mapped to its role in the architecture
- [[API Gateway]] — FastAPI entry point, httpx proxy to orchestrator
- [[LangGraph Orchestrator]] — LangGraph workflow, BackgroundTasks, lifespan, full run loop
- [[ResearchState]] — TypedDict state, how it flows between nodes
- [[PostgreSQL Models]] — SQLAlchemy async, Alembic, ResearchTask model
- [[Shared Logging]] — JSON logger factory used by every service
- [[Docker and Compose]] — Dockerfiles, layer caching, service healthchecks, networking

---

## Phase 2 Notes

- [[gRPC Agent Decomposition]] — overview: why gRPC, architecture diagram, proto generation commands
- [[Planner Agent]] — gRPC server, LangChain JSON planning, PlanRequest/PlanResponse
- [[Search Agent]] — Tavily web search, SearchResult message, multi-query loop
- [[Summarizer Agent]] — LLM summarization, JSON output, citations from URLs (not LLM)
- [[Critic Agent]] — quality scoring, missing_points, needs_more_research loop trigger
- [[Report Service]] — multi-summary synthesis, markdown output, final report
- [[gRPC Clients]] — orchestrator wrappers: channel pattern, stub, AioRpcError, dict conversion
- [[LangGraph Phase 2]] — how nodes changed, state accumulation across iterations, should_continue routing

---

## Concept Notes

- [[LangGraph Concepts]] — StateGraph, nodes, edges, conditional routing
- [[FastAPI Background Tasks]] — how BackgroundTasks works, the session lifecycle gotcha
- [[SQLAlchemy Async]] — engine, async_sessionmaker, Mapped columns, get_db
- [[gRPC]] — what gRPC is, how it works, vs REST, status codes, async model
- [[Protocol Buffers]] — typed contracts, field types, field numbers, generation, pb2 files
- [[gRPC aio Servers]] — async server pattern, servicer class, context.abort(), request lifecycle

---

## Alembic Notes

- [[Alembic Overview]] — what Alembic is, how it tracks history, migration chain, autogenerate
- [[Async Setup]] — why standard Alembic breaks with asyncpg, env.py annotated line by line
- [[Common Commands]] — every command with when to use it, Docker workflow
- [[Codex]] — one-page quick reference: files, commands, op operations, common mistakes

---

## Debugging Notes

- [[uv Cache Access Denied]] — sandboxed `uv` commands could not read the Windows user cache
- [[Docker Desktop Engine Missing]] — Docker build could not start because the Linux engine pipe was unavailable

---

## How to Use These Notes

- Every main note has a `file:` frontmatter pointing to the source file it documents.
- Use `[[Wikilinks]]` to jump between notes — never plain markdown links between notes.
- When you hit an error: fix it, then write a `[[debugging/Error Name]]` note before moving on.
