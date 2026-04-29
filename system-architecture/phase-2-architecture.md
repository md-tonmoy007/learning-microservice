# Phase 2 System Architecture

This document describes the current Phase 2 multi-service research assistant architecture.

## Service Architecture

```mermaid
flowchart LR
    user["User / Client"]

    subgraph compose["Docker Compose Network"]
        gateway["api-gateway\nFastAPI\n:8000"]
        orchestrator["orchestrator\nFastAPI + LangGraph\n:8001"]
        postgres[("postgres\nPostgreSQL 16\nresearch DB\n:5432")]

        planner["planner-agent\ngRPC PlannerService\n:50051"]
        search["search-agent\ngRPC SearchService\n:50052"]
        summarizer["summarizer-agent\ngRPC SummarizerService\n:50053"]
        critic["critic-agent\ngRPC CriticService\n:50054"]
        report["report-service\ngRPC ReportService\n:50055"]
    end

    openrouter["OpenRouter\nz-ai/glm-4.5-air:free"]
    tavily["Tavily Search API"]

    user -->|"HTTP POST /research\nHTTP GET /research/{task_id}"| gateway
    gateway -->|"HTTP /internal/research"| orchestrator

    orchestrator -->|"SQLAlchemy async\ncreate/read/update tasks"| postgres
    orchestrator -->|"gRPC CreatePlan"| planner
    orchestrator -->|"gRPC Search"| search
    orchestrator -->|"gRPC Summarize"| summarizer
    orchestrator -->|"gRPC Critique"| critic
    orchestrator -->|"gRPC GenerateReport"| report

    planner -->|"LLM calls"| openrouter
    summarizer -->|"LLM calls"| openrouter
    critic -->|"LLM calls"| openrouter
    report -->|"LLM calls"| openrouter
    search -->|"web search"| tavily
```

## Request Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Gateway as api-gateway
    participant Orchestrator as orchestrator
    participant DB as postgres
    participant Planner as planner-agent
    participant Search as search-agent
    participant Summarizer as summarizer-agent
    participant Critic as critic-agent
    participant Report as report-service
    participant OpenRouter as OpenRouter
    participant Tavily as Tavily

    User->>Gateway: POST /research {"query": "..."}
    Gateway->>Orchestrator: POST /internal/research
    Orchestrator->>DB: INSERT research_tasks(status="pending")
    Orchestrator-->>Gateway: 202 task_id
    Gateway-->>User: 202 task_id

    Orchestrator->>DB: UPDATE status="running"
    Orchestrator->>Planner: CreatePlan(task_id, user_query)
    Planner->>OpenRouter: Generate search plan
    OpenRouter-->>Planner: JSON plan
    Planner-->>Orchestrator: search_queries, report_sections

    loop Up to 3 critique iterations
        Orchestrator->>Search: Search(task_id, search_queries)
        Search->>Tavily: Search web
        Tavily-->>Search: Search results
        Search-->>Orchestrator: results

        Orchestrator->>Summarizer: Summarize(task_id, query, results)
        Summarizer->>OpenRouter: Summarize sources
        OpenRouter-->>Summarizer: JSON summary
        Summarizer-->>Orchestrator: summary, key_points, citations

        Orchestrator->>Critic: Critique(task_id, query, summary)
        Critic->>OpenRouter: Evaluate summary quality
        OpenRouter-->>Critic: JSON critique
        Critic-->>Orchestrator: score, missing_points, needs_more_research
    end

    Orchestrator->>Report: GenerateReport(task_id, query, summaries)
    Report->>OpenRouter: Synthesize final report
    OpenRouter-->>Report: Markdown report
    Report-->>Orchestrator: report_markdown
    Orchestrator->>DB: UPDATE status="completed", final_report

    User->>Gateway: GET /research/{task_id}
    Gateway->>Orchestrator: GET /internal/research/{task_id}
    Orchestrator->>DB: SELECT research_tasks
    DB-->>Orchestrator: task row
    Orchestrator-->>Gateway: task detail + final_report
    Gateway-->>User: final report
```

## Phase 2 Components

| Component | Role | Protocol | Port |
| --- | --- | --- | --- |
| `api-gateway` | Public HTTP entrypoint. Proxies research requests to the orchestrator. | HTTP/FastAPI | `8000` |
| `orchestrator` | Owns task persistence and LangGraph workflow execution. Calls agent services over gRPC. | HTTP/FastAPI + gRPC clients | `8001` |
| `postgres` | Stores `research_tasks`, status, iteration count, errors, and final reports. | PostgreSQL | `5432` |
| `planner-agent` | Converts the user query into search queries and report sections. | gRPC | `50051` |
| `search-agent` | Runs web searches through Tavily. | gRPC | `50052` |
| `summarizer-agent` | Summarizes search results and returns key points/citations. | gRPC | `50053` |
| `critic-agent` | Scores summary quality and decides whether more research is needed. | gRPC | `50054` |
| `report-service` | Synthesizes collected summaries into the final markdown report. | gRPC | `50055` |

## Runtime Configuration

The root `.env` provides the secrets used by Docker Compose:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=z-ai/glm-4.5-air:free
TAVILY_API_KEY=tvly-...
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
```

The orchestrator uses fixed Docker Compose service names for internal gRPC routing:

```env
PLANNER_AGENT_ADDRESS=planner-agent:50051
SEARCH_AGENT_ADDRESS=search-agent:50052
SUMMARIZER_AGENT_ADDRESS=summarizer-agent:50053
CRITIC_AGENT_ADDRESS=critic-agent:50054
REPORT_SERVICE_ADDRESS=report-service:50055
```

## Operational Notes

- Run the stack with `docker compose up --build`.
- Apply database migrations with `docker compose exec -T orchestrator uv run alembic upgrade head`.
- Submit work through `POST http://localhost:8000/research`.
- Poll status with `GET http://localhost:8000/research/{task_id}/status`.
- Fetch the final report with `GET http://localhost:8000/research/{task_id}`.
