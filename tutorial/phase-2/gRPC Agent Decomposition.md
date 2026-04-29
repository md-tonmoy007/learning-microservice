---
tags: [phase-2, grpc, microservices, langgraph]
file: services/orchestrator/app/graph/nodes.py
---

# gRPC Agent Decomposition

> Phase 2 moves agent work out of the orchestrator process and behind typed gRPC service contracts.

Related: [[Protocol Buffers]] · [[gRPC aio Servers]] · [[LangGraph Orchestrator]] · [[Home]]

---

## The Code

The orchestrator still owns the LangGraph workflow in `services/orchestrator/app/graph/workflow.py`.

The graph nodes in `services/orchestrator/app/graph/nodes.py` now call thin wrappers in `services/orchestrator/app/grpc_clients/`:

- planner calls `PlannerService.CreatePlan`
- search calls `SearchService.Search`
- summarizer calls `SummarizerService.Summarize`
- critic calls `CriticService.Critique`
- report calls `ReportService.GenerateReport`

Each agent has its own service folder under `services/` with a `pyproject.toml`, Dockerfile, async gRPC entrypoint, and business logic under `app/services/`.

## Walkthrough

Phase 1 kept planner, search, summarizer, critic, and report generation inside the orchestrator process. Phase 2 keeps the graph shape but changes the transport layer.

The important boundary is:

1. LangGraph node receives `ResearchState`
2. node maps state into a protobuf request
3. gRPC service does one stateless unit of work
4. node maps protobuf response back into partial state

> [!note]
> The graph is still the brain. The agent services are stateless workers. They do not decide which node runs next.

## Workflow

`docker-compose.yml` now starts the five gRPC services alongside the gateway, orchestrator, and Postgres.

Each image builds from the workspace root so Docker can copy `uv.lock`, all workspace `pyproject.toml` files, and the service source before running `uv sync --frozen --package <service>`.

The orchestrator receives agent addresses from settings:

- `PLANNER_AGENT_ADDRESS`
- `SEARCH_AGENT_ADDRESS`
- `SUMMARIZER_AGENT_ADDRESS`
- `CRITIC_AGENT_ADDRESS`
- `REPORT_SERVICE_ADDRESS`

Generated protobuf files live under `app/grpc_generated/` and are derived from `proto/*.proto`.
