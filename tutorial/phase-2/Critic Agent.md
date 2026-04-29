---
tags: [phase-2, grpc, langchain, critic, langgraph]
file: services/critic-agent/app/services/critic.py
---

# Critic Agent

> Evaluates the quality of a research summary, returns a quality score and a flag that tells LangGraph whether to loop back for more research.

Related: [[gRPC]] · [[Protocol Buffers]] · [[gRPC aio Servers]] · [[Summarizer Agent]] · [[Report Service]] · [[LangGraph Phase 2]] · [[Home]]

---

## The Code

**Proto contract** (`proto/critic.proto`):
```proto
service CriticService {
  rpc Critique (CritiqueRequest) returns (CritiqueResponse);
}

message CritiqueRequest {
  string task_id = 1;
  string user_query = 2;
  string summary = 3;
}

message CritiqueResponse {
  float score = 1;                    // 0.0 = terrible, 1.0 = excellent
  repeated string missing_points = 2; // topics not covered
  bool needs_more_research = 3;       // true = loop back to search
}
```

**Servicer** (`app/services/critic.py`):
```python
class CriticServicer(critic_pb2_grpc.CriticServiceServicer):
    async def Critique(self, request, context):
        prompt = f"""You are a research critic. Evaluate this summary for: {request.user_query}

Summary:
{request.summary}

Return a JSON object with:
- "score": float 0.0-1.0 (quality)
- "missing_points": list of topics not covered
- "needs_more_research": boolean

Return only valid JSON. No markdown fences."""

        try:
            response = await _llm.ainvoke([HumanMessage(content=prompt)])
            critique = json.loads(response.content)
        except Exception as exc:
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        return critic_pb2.CritiqueResponse(
            score=float(critique.get("score", 0.8)),
            missing_points=critique.get("missing_points") or [],
            needs_more_research=bool(critique.get("needs_more_research", False)),
        )
```

---

## Walkthrough

### The Three Output Fields

**`score` (float 0.0–1.0)**: A quality rating of the summary. 0.0 means the summary completely missed the topic; 1.0 means it's comprehensive and accurate. This is currently stored in `state["critique"]["score"]` but not used to gate the loop — only `needs_more_research` controls routing.

**`missing_points` (list of strings)**: Topics the LLM identified as absent from the summary. Example: `["quantum error correction", "current qubit count in real hardware"]`. These appear in the final state and could be used in future phases to direct additional search (e.g., re-query for missing topics specifically).

**`needs_more_research` (bool)**: The critical field. If `true`, the LangGraph `should_continue` function routes back to `search_web` for another pass. If `false` (or if `iteration_count >= 3`), the workflow advances to `generate_report`.

### The Default Fallback

```python
score=float(critique.get("score", 0.8)),
```

If the LLM returns JSON without a `"score"` key, the code defaults to `0.8`. This is an opinionated choice: if we can't evaluate, assume the summary is reasonably good (80%) rather than assuming it's bad (which might cause unnecessary looping). The `0.8` threshold is "good enough to proceed" in spirit.

### How This Drives the LangGraph Loop

The critic is the **decision point** of the entire workflow. Its `needs_more_research` field propagates into `state["critique"]`, which the `should_continue` function reads:

```python
def should_continue(state: ResearchState) -> str:
    critique = state.get("critique", {})
    if critique.get("needs_more_research") and state.get("iteration_count", 0) < 3:
        return "search_web"      # loop back
    return "generate_report"     # proceed to final report
```

The loop cap at 3 iterations prevents infinite loops in case the LLM always says more research is needed.

---

## Workflow

```
Orchestrator (critique_answer node)     Critic Agent (port 50054)
───────────────────────────────────     ─────────────────────────
summary = state["summaries"][-1]
critique_summary(
  task_id, user_query, summary)
  → open channel to critic-agent:50054
  → stub.Critique(CritiqueRequest)  ──►  CriticServicer.Critique()
                                          → build evaluation prompt
                                          → await _llm.ainvoke(prompt)
                                          → json.loads(response.content)
                                          → return CritiqueResponse(
                                              score=0.6,
                                              missing_points=["topic A"],
                                              needs_more_research=True,
                                            )
  ◄────── CritiqueResponse ──────────────
  → state["critique"] = {
      "score": 0.6,
      "missing_points": ["topic A"],
      "needs_more_research": True,
    }
  → state["iteration_count"] += 1

should_continue(state):
  → needs_more_research=True AND iteration_count=1 < 3
  → return "search_web"   ← loops back!
```

> [!tip]
> The critic only sees the **latest summary** (`state["summaries"][-1]`). It doesn't compare across iterations. If the workflow loops twice, the second critique evaluates the second summary independently — it doesn't know what was missing in the first pass.

> [!warning]
> The `score` field uses `float` in the proto. Proto's `float` is a 32-bit IEEE 754 number. The LLM might return `0.75`, which becomes `0.75` in Python. Don't compare with `==` — use `>=` thresholds instead (`if score >= 0.8`).

> [!note]
> The critic prompt sends the **full summary text**. For a long summary (1,000+ words), this uses significant LLM context. In Phase 5 (Qdrant), we might instead embed and compare against a quality rubric rather than passing full text to the LLM each time.
