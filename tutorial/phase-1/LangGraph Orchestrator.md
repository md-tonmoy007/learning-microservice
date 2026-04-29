---
tags: [phase-1, langgraph, orchestrator, fastapi]
file: services/orchestrator/app/graph/workflow.py
---

# LangGraph Orchestrator

> The brain of the system. Owns the research workflow: receives a query, runs it through a LangGraph state machine, and persists the result to PostgreSQL.

Related: [[ResearchState]] · [[LangGraph Concepts]] · [[FastAPI Background Tasks]] · [[PostgreSQL Models]] · [[Project Structure]] · [[Home]]

---

## The Code

**Workflow graph:** `services/orchestrator/app/graph/workflow.py`
**Node functions:** `services/orchestrator/app/graph/nodes.py`
**State definition:** `services/orchestrator/app/graph/state.py`
**Service layer:** `services/orchestrator/app/services/research.py`
**API routes:** `services/orchestrator/app/api/research.py`

---

## Walkthrough

### FastAPI lifespan — startup and shutdown

`app/main.py` uses the `lifespan` context manager instead of deprecated `on_event` hooks:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield                    # everything before yield = startup
    await engine.dispose()   # everything after yield = shutdown

app = FastAPI(lifespan=lifespan)
```

The `yield` separates startup from shutdown logic. Code before `yield` runs when the app starts; code after runs when it shuts down gracefully (e.g., `Ctrl+C` or `docker compose down`).

`engine.dispose()` closes all open database connections in the connection pool. Without this, the process exits with open connections, which PostgreSQL logs as errors. The gateway's `main.py` does not have a lifespan because it has no resources to clean up — no database engine.

### The big picture

The orchestrator does two things:
1. **HTTP server** (FastAPI) — exposes `/internal/research` endpoints called by the gateway
2. **LangGraph runner** — when a task is created, it runs a stateful multi-step AI workflow in the background

These two concerns are kept separate: routes are in `app/api/`, graph logic is in `app/graph/`.

### The LangGraph workflow

```
plan_research → search_web → summarize_results → critique_answer
                                                        ↓
                                              [should_continue?]
                                               ↙           ↘
                                         search_web    generate_report → END
                                         (loop back)
```

This is a `StateGraph`. Each box is a **node** (a Python async function). The arrows are **edges**. The decision box is a **conditional edge** — it calls `should_continue()` to pick the next node.

### Nodes — what each one does

**`plan_research`** — calls the LLM, asks it to generate search queries and report sections from the user question. Returns the list of queries as `research_plan`.

**`search_web`** — calls Tavily's search API for each query in `research_plan`. Accumulates raw results in `search_results` (list of dicts with url + content).

**`summarize_results`** — calls the LLM with the last 10 search results. Writes a human-readable summary, preserving sources. Appends to `summaries`.

**`critique_answer`** — calls the LLM as a critic. Asks it to score the quality and list missing points. Returns JSON with `score`, `missing_points`, and `needs_more_research`. Increments `iteration_count`.

**`generate_report`** — calls the LLM with all summaries combined. Writes the final markdown report.

### Conditional edge — the loop

```python
def should_continue(state: ResearchState) -> str:
    critique = state.get("critique", {})
    if critique.get("needs_more_research") and state.get("iteration_count", 0) < 3:
        return "search_web"
    return "generate_report"
```

This function returns a string. The string must match a key in the `path_map` dict passed to `add_conditional_edges`. LangGraph uses it to pick the next node.

The `iteration_count < 3` guard prevents infinite loops if the critic always returns `needs_more_research: true`.

### Building and compiling the graph

```python
graph = StateGraph(ResearchState)
graph.add_node("plan_research", plan_research)
# ... add all nodes
graph.set_entry_point("plan_research")
graph.add_edge("plan_research", "search_web")
# ... add all edges
graph.add_conditional_edges("critique_answer", should_continue, {...})
research_graph = graph.compile()
```

`graph.compile()` returns a `CompiledGraph` object. This is what you call `ainvoke()` on. The compiled graph is created once at module import time (not per request) — it's stateless.

### Running the graph — `ainvoke`

```python
final_state = await research_graph.ainvoke(initial_state)
```

`ainvoke` runs the whole workflow from the entry point to END. It returns the final state dict. Every node's returned partial dict is merged into the state before the next node runs.

### The service layer

`app/services/research.py` owns the interaction between FastAPI and LangGraph:

```python
async def run_workflow(task_id: str, query: str) -> None:
    async with AsyncSessionFactory() as db:
        task = await get_task(db, task_id)
        task.status = "running"
        await db.commit()
        try:
            final_state = await research_graph.ainvoke(initial_state)
            task.status = final_state["status"]
            task.final_report = final_state["final_report"]
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
        await db.commit()
```

Notice: **`AsyncSessionFactory()` creates a fresh DB session**. The HTTP request's session is already closed by the time `run_workflow` runs. See [[FastAPI Background Tasks]] for why.

---

## Workflow

```
POST /internal/research {"query": "..."}
  → api/research.py: create_research()
    → services/research.py: create_task(db, query)
      → INSERT into research_tasks, status="pending"
    → background_tasks.add_task(run_workflow, task.id, query)
  → returns 202 with task_id immediately

[Background task fires after response is sent]
  → run_workflow(task_id, query)
    → UPDATE status="running"
    → research_graph.ainvoke(initial_state)
      → plan_research → search_web → summarize → critique → [loop?] → report
    → UPDATE status="completed", final_report=...
```

> [!note] Phase 2 change
> In Phase 2, each node in `nodes.py` will make a gRPC call to a separate microservice instead of calling LangChain directly. The LangGraph graph structure in `workflow.py` does not change at all — only the transport inside each node changes.

> [!warning] LLM module-level instantiation
> `_llm = ChatOpenRouter(...)` is created once at import time. If `OPENROUTER_API_KEY` is not set when the service starts, this will fail at import. Always set the env var before starting the service.
