---
tags: [phase-2, langgraph, orchestrator, workflow]
file: services/orchestrator/app/graph/nodes.py
---

# LangGraph Phase 2

> In Phase 2, the LangGraph nodes no longer contain LLM logic. Each node is a thin wrapper that calls one gRPC client function and maps the response back into ResearchState.

Related: [[gRPC Clients]] · [[LangGraph Orchestrator]] · [[ResearchState]] · [[Planner Agent]] · [[Search Agent]] · [[Summarizer Agent]] · [[Critic Agent]] · [[Report Service]] · [[Home]]

---

## The Code

**All five nodes** (`app/graph/nodes.py`):
```python
async def plan_research(state: ResearchState) -> dict:
    plan = await create_plan(state["task_id"], state["user_query"])
    return {
        "research_plan": plan["search_queries"],
        "report_sections": plan["report_sections"],
        "status": "planned",
    }

async def search_web(state: ResearchState) -> dict:
    new_results = await search_queries(state["task_id"], state["research_plan"][:3])
    return {
        "search_results": state.get("search_results", []) + new_results,
        "status": "searched",
    }

async def summarize_results(state: ResearchState) -> dict:
    summary = await summarize_search_results(
        task_id=state["task_id"],
        user_query=state["user_query"],
        results=state["search_results"][-10:],
    )
    return {
        "summaries": state.get("summaries", []) + [summary["summary"]],
        "status": "summarized",
    }

async def critique_answer(state: ResearchState) -> dict:
    summary = state["summaries"][-1] if state["summaries"] else ""
    critique = await critique_summary(
        task_id=state["task_id"],
        user_query=state["user_query"],
        summary=summary,
    )
    return {
        "critique": critique,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "status": "critiqued",
    }

async def generate_report(state: ResearchState) -> dict:
    report = await generate_final_report(
        task_id=state["task_id"],
        user_query=state["user_query"],
        summaries=state.get("summaries", []),
    )
    return {"final_report": report, "status": "completed"}
```

**The routing function** (conditional edge):
```python
def should_continue(state: ResearchState) -> str:
    critique = state.get("critique", {})
    if critique.get("needs_more_research") and state.get("iteration_count", 0) < 3:
        return "search_web"
    return "generate_report"
```

---

## Walkthrough

### How the Graph Is Wired (`app/graph/workflow.py`)

```python
graph.add_node("plan_research", plan_research)
graph.add_node("search_web", search_web)
graph.add_node("summarize_results", summarize_results)
graph.add_node("critique_answer", critique_answer)
graph.add_node("generate_report", generate_report)

graph.add_edge(START, "plan_research")
graph.add_edge("plan_research", "search_web")
graph.add_edge("search_web", "summarize_results")
graph.add_edge("summarize_results", "critique_answer")
graph.add_conditional_edges("critique_answer", should_continue)
graph.add_edge("generate_report", END)
```

`add_conditional_edges("critique_answer", should_continue)` means: after `critique_answer` runs, call `should_continue(state)`. If it returns `"search_web"`, go to `search_web`. If it returns `"generate_report"`, go to `generate_report`. LangGraph expects the string keys to match node names.

### Phase 1 vs Phase 2 — What Changed in the Nodes

**Phase 1** (before gRPC was added) — nodes contained LLM logic directly:
```python
# Phase 1 plan_research node
async def plan_research(state: ResearchState) -> dict:
    llm = ChatOpenRouter(
        model="z-ai/glm-4.5-air:free",
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
    response = await llm.ainvoke([HumanMessage(content=f"Plan research for: {state['user_query']}")])
    # ... parse response ...
    return {"research_plan": [...]}
```

**Phase 2** — nodes delegate over the network:
```python
# Phase 2 plan_research node
async def plan_research(state: ResearchState) -> dict:
    plan = await create_plan(state["task_id"], state["user_query"])  # gRPC call
    return {"research_plan": plan["search_queries"], ...}
```

The node shape is the same (takes state, returns partial dict). The difference is where the work happens: locally (Phase 1) vs across the network (Phase 2). LangGraph doesn't know or care — it just calls the function.

### How State Accumulates Over the Loop

When the critic says `needs_more_research=True`:

```
Iteration 1:
  search_web:       state["search_results"] = [r1, r2, ..., r10]
  summarize_results: state["summaries"] = ["summary1"]
  critique_answer:  state["critique"] = {needs_more_research: true}
                    state["iteration_count"] = 1

Iteration 2 (loop):
  search_web:       state["search_results"] = [r1...r10, r11...r20]  ← appended
  summarize_results: state["summaries"] = ["summary1", "summary2"]   ← appended
  critique_answer:  state["critique"] = {needs_more_research: false}
                    state["iteration_count"] = 2

generate_report:
  sends summaries=["summary1", "summary2"] to report service
```

Key observation: `search_results` and `summaries` grow with each loop because nodes use `state.get(..., []) + new_items`. If the list were replaced instead of appended, previous iterations' data would be lost.

### The Iteration Cap

```python
if critique.get("needs_more_research") and state.get("iteration_count", 0) < 3:
```

Without the `< 3` guard, a critic that always returns `needs_more_research=True` would loop forever. The cap at 3 means the worst case is 3 search passes before forcing a report. This is a deliberate cost control measure: 3 iterations × 3 queries × 5 results = up to 45 web pages read, 3 LLM summarize calls, and 3 LLM critique calls.

---

## Full Workflow Diagram (Phase 2)

```
User query arrives at API gateway → orchestrator POST /internal/research
  ↓
run_workflow() starts as BackgroundTask
  ↓
research_graph.ainvoke(initial_state)
  ↓
┌─ plan_research ──────────► planner-agent:50051 (gRPC)
│                              Returns: search_queries, report_sections
│   ↓
├─ search_web ─────────────► search-agent:50052 (gRPC)
│                              Searches up to 3 queries × 5 results
│   ↓
├─ summarize_results ──────► summarizer-agent:50053 (gRPC)
│                              LLM summarizes last 10 results
│   ↓
├─ critique_answer ────────► critic-agent:50054 (gRPC)
│                              LLM evaluates quality
│   ↓
├─ should_continue?
│   ├─ needs_more_research=True AND iteration < 3 → back to search_web ↑
│   └─ otherwise ↓
│
└─ generate_report ────────► report-service:50055 (gRPC)
                               LLM synthesizes all summaries → markdown
  ↓
state["final_report"] saved to PostgreSQL
task.status = "completed"
```

> [!tip]
> Every node returns only the fields it changes. LangGraph merges the returned dict into the full state — fields not mentioned are preserved unchanged. This is why `search_web` doesn't need to return `user_query` even though the state has it.

> [!note]
> `should_continue` is a plain Python function, not `async`. It doesn't do any I/O — it just reads `state` and returns a string. LangGraph calls it synchronously after `critique_answer` finishes.
