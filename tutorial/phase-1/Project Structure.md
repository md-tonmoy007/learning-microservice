---
tags: [phase-1, architecture, structure]
file: docker-compose.yml
---

# Project Structure

> Every folder and file in the Phase 1 codebase and what role it plays in the architecture.

Related: [[API Gateway]] · [[LangGraph Orchestrator]] · [[PostgreSQL Models]] · [[ResearchState]] · [[Docker and Compose]] · [[Home]]

---

## The Big Picture

Phase 1 has two running services plus shared infrastructure:

```
User
  │  HTTP
  ▼
api-gateway  (port 8000)  — public-facing proxy
  │  HTTP (httpx)
  ▼
orchestrator (port 8001)  — workflow brain
  │  asyncpg
  ▼
postgres     (port 5432)  — task persistence
```

Everything below maps to this diagram.

---

## Root Level

```
d:/learning-microservice/
├── services/           ← one folder per running service
├── shared/             ← code shared across services
├── proto/              ← gRPC contracts (Phase 2, not compiled yet)
├── docker-compose.yml  ← wires all services together
├── .env.example        ← root-level env template
└── pyproject.toml      ← workspace-level uv config
```

### `services/`
Each subfolder is one independently deployable service. Each has its own `pyproject.toml`, its own `Dockerfile`, and its own `.env`. They share nothing at the filesystem level — only via network calls.

### `shared/`
Python code that multiple services import. In Phase 1 only `logging.py` lives here. Shared code is installed as a local package via `uv add --editable ../../shared` in each service's `pyproject.toml`.

### `proto/`
`.proto` files define the gRPC contracts for Phase 2 agents. They are **not compiled** in Phase 1 — they are placeholders showing what the API surface will look like. Stubs will be generated into `app/grpc_generated/` inside each service when Phase 2 starts.

### `docker-compose.yml`
The single file that describes how all services, databases, and volumes connect. In Phase 1 it defines: `api-gateway`, `orchestrator`, `postgres`. See [[Docker and Compose]].

---

## `services/api-gateway/`

```
services/api-gateway/
├── app/
│   ├── main.py             ← FastAPI app, mounts router, /health
│   ├── api/
│   │   └── research.py     ← three route handlers (POST, GET, GET/status)
│   ├── core/
│   │   └── config.py       ← pydantic-settings, reads ORCHESTRATOR_URL
│   └── schemas/
│       └── research.py     ← Pydantic request/response models
├── Dockerfile
├── pyproject.toml
└── .env.example
```

| File | What it does |
|------|-------------|
| `app/main.py` | Creates the `FastAPI()` app, includes the router at `/research`, exposes `/health` |
| `app/api/research.py` | The three endpoints: `POST /research`, `GET /research/{id}`, `GET /research/{id}/status`. Each is a thin httpx call to the orchestrator |
| `app/core/config.py` | Reads `ORCHESTRATOR_URL` from env. Default: `http://orchestrator:8001` |
| `app/schemas/research.py` | `ResearchRequest` (query: str), `ResearchResponse` (task_id, status, message), `TaskStatusResponse`, `TaskDetailResponse` |

The gateway has **no database**, **no LLM calls**, and **no business logic**. If you add anything here beyond forwarding, something is wrong.

---

## `services/orchestrator/`

```
services/orchestrator/
├── app/
│   ├── main.py             ← FastAPI app with lifespan, mounts router at /internal
│   ├── api/
│   │   └── research.py     ← create, get, get_status endpoints (internal)
│   ├── core/
│   │   ├── config.py       ← reads POSTGRES_URL, OPENROUTER_API_KEY, TAVILY_API_KEY
│   │   └── database.py     ← engine, AsyncSessionFactory, Base, get_db
│   ├── graph/
│   │   ├── state.py        ← ResearchState TypedDict
│   │   ├── nodes.py        ← 5 async node functions + should_continue
│   │   └── workflow.py     ← builds and compiles the StateGraph
│   ├── models/
│   │   └── research.py     ← ResearchTask SQLAlchemy ORM model
│   ├── schemas/
│   │   └── research.py     ← Pydantic models for the internal API
│   └── services/
│       └── research.py     ← create_task, get_task, run_workflow
├── alembic/
│   ├── env.py              ← async Alembic config
│   └── versions/           ← generated migration scripts
├── alembic.ini
├── Dockerfile
├── pyproject.toml
└── .env.example
```

### `app/main.py`
Creates the FastAPI app. Uses `lifespan` to dispose the database engine on shutdown. Mounts the router at `/internal/research`. Exposes `/health`.

### `app/api/research.py`
Three endpoints prefixed `/internal/research`:
- `POST /` → creates a task in the DB, fires `run_workflow` as a background task, returns 202
- `GET /{task_id}` → returns full task detail
- `GET /{task_id}/status` → returns just status

"Internal" in the prefix signals these are not for public clients — only the gateway calls them.

### `app/core/config.py`
Reads: `POSTGRES_URL`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `TAVILY_API_KEY`, `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`.

### `app/core/database.py`
Three exports that the whole orchestrator depends on:
- `engine` — the async SQLAlchemy engine, one per process
- `AsyncSessionFactory` — creates sessions for background tasks
- `get_db` — FastAPI dependency that yields a session per HTTP request
- `Base` — all ORM models inherit from this

See [[SQLAlchemy Async]] and [[PostgreSQL Models]].

### `app/graph/`
The LangGraph workflow. Three files with strict separation:

| File | Rule |
|------|------|
| `state.py` | Only the `TypedDict`. No logic. |
| `nodes.py` | Only node functions and `should_continue`. No graph wiring. |
| `workflow.py` | Only graph construction. No business logic. |

See [[ResearchState]] and [[LangGraph Orchestrator]].

### `app/models/research.py`
`ResearchTask` — the only ORM model in Phase 1. Maps to the `research_tasks` table. See [[PostgreSQL Models]].

### `app/schemas/research.py`
Pydantic models for the internal API: `CreateResearchRequest`, `ResearchResponse`, `TaskDetailResponse`, `TaskStatusResponse`. Separate from the gateway's schemas so each service owns its own contract.

### `app/services/research.py`
The **service layer** — business logic that sits between the API and the graph:
- `create_task(db, query)` → inserts into DB, returns `ResearchTask`
- `get_task(db, task_id)` → SELECT by ID
- `run_workflow(task_id, query)` → runs the full LangGraph invocation, updates DB on completion

This is the only place `research_graph.ainvoke()` is called. Routes never touch the graph directly.

### `alembic/`
Schema migration history. `env.py` is the async-aware entry point. `versions/` holds generated migration scripts. See [[PostgreSQL Models]].

---

## `shared/`

```
shared/
├── logging.py     ← get_logger() factory, JSON formatter
├── __init__.py
└── pyproject.toml
```

### `shared/logging.py`
One function: `get_logger(service_name: str) -> logging.Logger`. Returns a logger that writes structured JSON to stdout. See [[Shared Logging]].

---

## `proto/`

```
proto/
├── planner.proto     ← PlannerService.CreatePlan
├── search.proto      ← SearchService.Search
├── summarizer.proto  ← SummarizerService.Summarize (implied)
├── critic.proto      ← CriticService.Critique (implied)
└── report.proto      ← ReportService.GenerateReport (implied)
```

All Phase 2 placeholders. Not compiled, not used in Phase 1. They exist so you can see what the inter-service contracts will look like before you build them.

---

## How a Request Flows Through the Files

```
1. User hits POST /research
   → services/api-gateway/app/api/research.py: submit_research()

2. Gateway proxies to orchestrator
   → services/orchestrator/app/api/research.py: create_research()
   → services/orchestrator/app/services/research.py: create_task()
   → services/orchestrator/app/models/research.py: ResearchTask (INSERT)
   → background_tasks.add_task(run_workflow, task_id, query)

3. Response returns immediately: {"task_id": "...", "status": "pending"}

4. Background task fires
   → services/orchestrator/app/services/research.py: run_workflow()
   → services/orchestrator/app/graph/workflow.py: research_graph.ainvoke()
   → services/orchestrator/app/graph/nodes.py: plan_research → search_web → summarize → critique → report
   → services/orchestrator/app/models/research.py: ResearchTask (UPDATE status/report)

5. User polls GET /research/{id}/status
   → api-gateway proxies → orchestrator → DB SELECT → returns status

6. User fetches GET /research/{id} when status="completed"
   → returns full TaskDetailResponse with final_report
```

> [!tip] Read the code in this order
> Start with `state.py` (understand what data flows), then `nodes.py` (what each step does), then `workflow.py` (how steps connect), then `services/research.py` (how it's triggered), then `api/research.py` (how HTTP reaches the service layer).
