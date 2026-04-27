---
tags: [phase-1, langgraph, state, typeddict]
file: services/orchestrator/app/graph/state.py
---

# ResearchState

> The single source of truth for one research workflow run. LangGraph passes this dict through every node in the graph.

Related: [[LangGraph Orchestrator]] · [[LangGraph Concepts]] · [[Home]]

---

## The Code

```python
# services/orchestrator/app/graph/state.py
from typing import TypedDict

class ResearchState(TypedDict):
    task_id: str
    user_query: str
    research_plan: list[str]
    search_results: list[dict]
    summaries: list[str]
    critique: dict
    final_report: str
    iteration_count: int
    status: str
```

---

## Walkthrough

### What is TypedDict?

`TypedDict` is a Python type that looks and behaves like a regular dict at runtime, but gives you static type checking. It's the right choice for LangGraph state because:

- LangGraph internally merges partial state updates — it needs a dict, not a class instance.
- Type checkers (mypy, pyright) can verify that node functions return the right keys.
- IDE autocomplete works on state fields.

Compare to Pydantic:
```python
# Pydantic (doesn't work with LangGraph's merge mechanism)
class ResearchState(BaseModel):
    task_id: str

# TypedDict (works — it's a plain dict with type hints)
class ResearchState(TypedDict):
    task_id: str
```

### How state flows between nodes

Each node receives the **full current state** as input. Each node returns only the fields it wants to **update**:

```python
async def plan_research(state: ResearchState) -> dict:
    # receives the full state
    # returns only the fields that change
    return {
        "research_plan": ["query 1", "query 2"],
        "status": "planned",
    }
```

LangGraph merges this partial return into the full state before calling the next node. Fields not returned are unchanged.

### Field-by-field explanation

| Field             | Set by             | Used by                       |
|------------------|--------------------|-------------------------------|
| `task_id`         | `run_workflow`     | tracing, logging              |
| `user_query`      | `run_workflow`     | every node (context)          |
| `research_plan`   | `plan_research`    | `search_web` (queries to run) |
| `search_results`  | `search_web`       | `summarize_results`           |
| `summaries`       | `summarize_results`| `critique_answer`, `generate_report` |
| `critique`        | `critique_answer`  | `should_continue` (loop decision) |
| `final_report`    | `generate_report`  | saved to DB                   |
| `iteration_count` | `critique_answer`  | `should_continue` (loop guard)|
| `status`          | every node         | DB status column              |

### Why lists grow across iterations

`search_results` and `summaries` use this accumulation pattern:

```python
return {
    "search_results": state.get("search_results", []) + new_results,
}
```

On the first pass: `[] + [result1, result2]` → `[result1, result2]`
On the second pass (if critic loops back): `[result1, result2] + [result3]` → `[result1, result2, result3]`

The summarizer always reads the **last 10** results (`search_results[-10:]`) so it doesn't get overwhelmed on repeated loops.

### Why `critique` is a plain dict

```python
critique: dict
# not: critique: CritiqueSchema
```

The LLM returns a JSON string that we parse with `json.loads`. We don't validate it with Pydantic because:
- The LLM sometimes returns slightly malformed JSON — we have a fallback.
- We only read two keys: `needs_more_research` and `score`. Using `.get()` is safe.

> [!tip] Phase 2 change
> When agents become gRPC services, the planner response will be a proto message instead of JSON. `research_plan` will be populated from `response.search_queries` (a proto repeated field) instead of `json.loads(response.content)`.

> [!warning] Shared state is per-invocation
> Each `research_graph.ainvoke(initial_state)` starts from a fresh copy of `initial_state`. There is no shared mutable state between concurrent research tasks — each gets its own state dict.
