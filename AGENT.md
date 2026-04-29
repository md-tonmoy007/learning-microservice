# AGENT.md — Codex Working Guide

## Purpose
This repository is a **personal learning project** for building a multi-agent research assistant step by step. The point is not just to make it work, but to understand why each architectural choice exists: microservices boundaries, LangGraph orchestration, event-driven workflows, persistence, and production infrastructure.

Codex should optimize for:
- Small, teachable increments
- Accurate alignment with the repo's **current phase**
- Clear documentation alongside code changes

## Current Reality vs Planned Architecture
The long-term plan includes multiple gRPC agent services, Kafka/Redpanda, Redis, Qdrant, observability, and Kubernetes.

The **current repo** is still in **Phase 1**:
- `services/api-gateway` is the public FastAPI entrypoint
- `services/orchestrator` owns the LangGraph workflow and PostgreSQL persistence
- Planner/search/summarize/critique/report steps currently run **in-process** inside the orchestrator
- `docker-compose.yml` currently starts only:
  - `api-gateway`
  - `orchestrator`
  - `postgres`

Do not assume later-phase services already exist just because they are described in docs. Treat `docs/` and `CLAUDE.md` as the roadmap, and the code under `services/` as source of truth for implementation.

## How Codex Should Work Here
- Make **small, focused changes**. Prefer one concept, one fix, or one service at a time.
- After every meaningful code change, add or update a matching note in `tutorial/`.
- When something breaks, fix it and write a debugging note in `tutorial/debugging/`.
- Preserve the repo's learning value. Favor readable code and explicit structure over clever shortcuts.
- Build the MVP first. Do not add Kubernetes, Kafka, Redis, Qdrant, or extra infra unless the task specifically calls for the next phase.

## Tutorial Rules
The `tutorial/` directory is a personal Obsidian vault and should be kept in sync with meaningful changes.

### Required note types
- Main notes: `tutorial/<topic>/Note Name.md`
- Concept notes: `tutorial/concepts/Concept Name.md`
- Debugging notes: `tutorial/debugging/Error Name.md`

### Obsidian conventions
- Add YAML frontmatter with `tags:` to every note
- Use `[[Wikilinks]]` between notes, not normal markdown links
- Use callouts like `> [!note]`, `> [!tip]`, and `> [!warning]`
- Include `[[Home]]` in every main note
- Use Title Case filenames with spaces

### Debugging note minimum content
Every debugging note should include:
- The exact error message or symptom
- What caused it
- How it was diagnosed
- How it was fixed

Also link the note to relevant code files and related tutorial notes, and add it to the debugging section of `tutorial/Home.md`.

## Package Management
Use `uv`, not `pip`.

Typical commands:
```bash
uv sync
uv add <package>
uv add --dev <package>
```

Important:
- This is a workspace repo with members in `services/*` and `shared`
- Each service has its own `pyproject.toml`
- Run service-specific dependency commands from inside that service directory

## Running the Current Project
From the repo root:

```bash
docker compose up --build
docker compose exec orchestrator uv run alembic upgrade head
```

Services exposed today:
- API Gateway: `http://localhost:8000`
- Orchestrator: `http://localhost:8001`
- Postgres: `localhost:5432`

Useful endpoints:
- `POST /research` on the gateway to submit a task
- `GET /research/{task_id}` on the gateway for the final result
- `GET /research/{task_id}/status` on the gateway for polling
- `POST /internal/research` on the orchestrator is internal-only

## Repo Map
### Active code
- `services/api-gateway/app/api/research.py`
  - Proxies public HTTP requests to the orchestrator via `httpx`
- `services/orchestrator/app/api/research.py`
  - Creates tasks and starts the workflow in a `BackgroundTask`
- `services/orchestrator/app/services/research.py`
  - Persists task state and runs the LangGraph workflow with a fresh DB session
- `services/orchestrator/app/graph/workflow.py`
  - Defines the graph edges and critique loop
- `services/orchestrator/app/graph/nodes.py`
  - Contains the current in-process planner/search/summarize/critique/report steps
- `services/orchestrator/app/graph/state.py`
  - Defines the shared `ResearchState` `TypedDict`
- `services/orchestrator/app/models/research.py`
  - Stores `research_tasks` rows in PostgreSQL
- `shared/logging.py`
  - Shared utilities area, currently minimal

### Roadmap and design docs
- `CLAUDE.md` describes the intended working style and long-term architecture
- `docs/architecture.md` explains the phased target design
- `docs/phase-1.md` through `docs/phase-6.md` describe the rollout path

## Implementation Conventions
- In LangGraph work, add new state fields to `app/graph/state.py` first
- Keep node logic in `app/graph/nodes.py`
- Keep graph wiring and conditional edges in `app/graph/workflow.py`
- Remember that the workflow runs in a FastAPI background task, so it must create its **own** DB session
- Prefer explicit Pydantic schemas and SQLAlchemy models over ad hoc dict contracts at API boundaries
- Keep gateway code thin; business logic belongs in the orchestrator

## Environment
- Copy each service's `.env.example` to `.env` when needed
- Never commit secrets
- The current orchestrator depends on:
  - `OPENROUTER_API_KEY`
  - `OPENROUTER_MODEL` (defaults to `z-ai/glm-4.5-air:free` in LLM agent services)
  - `TAVILY_API_KEY`
  - `POSTGRES_URL`
- Optional tracing settings exist but are not required for Phase 1:
  - `LANGCHAIN_TRACING_V2`
  - `LANGCHAIN_API_KEY`

## What Codex Should Avoid
- Do not silently implement future-phase architecture as if it already exists
- Do not make bulk refactors unless explicitly requested
- Do not skip tutorial updates for meaningful code changes
- Do not replace `uv` workflows with `pip`
- Do not move orchestration logic into the gateway

## Definition of a Good Change
A good change in this repo usually has three parts:
1. A focused code change
2. A matching tutorial or debugging note
3. A short explanation of what concept was learned or reinforced
