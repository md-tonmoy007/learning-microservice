---
tags: [concept, langgraph, stategraph]
---

# LangGraph Concepts

> Core concepts needed to understand and build with LangGraph StateGraph.

Used in: [[LangGraph Orchestrator]] · [[ResearchState]]

---

## What is LangGraph?

LangGraph is a library for building stateful, multi-step AI applications as graphs. You define:
- **State** — a TypedDict shared across all steps
- **Nodes** — async functions that read state and return partial updates
- **Edges** — how nodes connect (fixed or conditional)

The graph runs by calling `graph.ainvoke(initial_state)`, which executes nodes in order until it reaches `END`.

---

## StateGraph

`StateGraph(StateType)` is the graph builder. You build it, then call `.compile()` to get a runnable object.

```python
from langgraph.graph import StateGraph, END
from app.graph.state import ResearchState

graph = StateGraph(ResearchState)
# ... add nodes and edges
compiled = graph.compile()
```

The compiled graph is **immutable and stateless** — it's safe to create once at module import time and reuse across many concurrent `ainvoke()` calls.

---

## Nodes

A node is any async (or sync) callable that takes the state and returns a partial state dict:

```python
async def plan_research(state: ResearchState) -> dict:
    # read from state
    query = state["user_query"]
    # do work
    queries = ["query 1", "query 2"]
    # return only changed fields
    return {"research_plan": queries, "status": "planned"}
```

**Rules:**
- Return only the fields you change — don't return the whole state
- Returning `{}` is valid (no changes)
- Raising an exception aborts the workflow

---

## Edges

**Fixed edge** — always goes from A to B:
```python
graph.add_edge("plan_research", "search_web")
```

**Entry point** — the first node to run:
```python
graph.set_entry_point("plan_research")
```

**END** — the terminal node. When a node's edge points to END, the workflow finishes and `ainvoke` returns the final state:
```python
graph.add_edge("generate_report", END)
```

---

## Conditional Edges

A conditional edge calls a function to decide the next node at runtime:

```python
def should_continue(state: ResearchState) -> str:
    if state["critique"].get("needs_more_research") and state["iteration_count"] < 3:
        return "search_web"
    return "generate_report"

graph.add_conditional_edges(
    "critique_answer",      # from this node
    should_continue,        # call this function to pick next node
    {                       # map return value → node name
        "search_web": "search_web",
        "generate_report": "generate_report",
    },
)
```

The function must return a string matching a key in the path_map. If it returns an unmapped value, LangGraph raises an error.

---

## State Merging

After each node, LangGraph merges the returned partial dict into the accumulated state:

```
State before node:  {"user_query": "...", "research_plan": [], "status": "pending"}
Node returns:       {"research_plan": ["q1", "q2"], "status": "planned"}
State after node:   {"user_query": "...", "research_plan": ["q1", "q2"], "status": "planned"}
```

Fields not returned by the node are **unchanged**. This is why nodes return partial dicts instead of the full state.

---

## ainvoke vs invoke

```python
# Async (use this in FastAPI / async contexts)
final_state = await graph.ainvoke(initial_state)

# Sync (use in scripts)
final_state = graph.invoke(initial_state)
```

Always use `ainvoke` inside FastAPI because you're in an async event loop. Using the sync `invoke` would block the event loop.

---

## Why LangGraph (not just chained LLM calls)?

| Feature              | Plain chained calls | LangGraph                      |
|---------------------|--------------------|---------------------------------|
| State management    | Manual             | Automatic merge per node        |
| Conditional routing | Manual if/else     | Declarative conditional edges   |
| Loops               | Recursion / while  | Built-in (node can point back)  |
| Observability       | Manual logging     | LangSmith traces every node     |
| Resumability        | Hard               | Checkpointing (Phase 5+)        |
