---
tags: [phase-2, grpc, langchain, planner]
file: services/planner-agent/app/services/planner.py
---

# Planner Agent

> Receives the user's research question, asks an LLM to generate search queries and report section headings, and returns them as a gRPC response.

Related: [[gRPC]] · [[Protocol Buffers]] · [[gRPC aio Servers]] · [[gRPC Clients]] · [[gRPC Agent Decomposition]] · [[Home]]

---

## The Code

**Proto contract** (`proto/planner.proto`):
```proto
service PlannerService {
  rpc CreatePlan (PlanRequest) returns (PlanResponse);
}

message PlanRequest {
  string task_id = 1;
  string user_query = 2;
}

message PlanResponse {
  repeated string search_queries = 1;
  repeated string report_sections = 2;
}
```

**gRPC server** (`app/main.py`):
```python
async def serve() -> None:
    server = grpc.aio.server()
    planner_pb2_grpc.add_PlannerServiceServicer_to_server(PlannerServicer(), server)
    server.add_insecure_port(f"[::]:{settings.grpc_port}")
    await server.start()
    await server.wait_for_termination()
```

**Servicer** (`app/services/planner.py`):
```python
class PlannerServicer(planner_pb2_grpc.PlannerServiceServicer):
    async def CreatePlan(self, request, context):
        prompt = f"""You are a research planner. Given the user question, return a JSON object with:
- "search_queries": list of 3-5 specific search queries
- "report_sections": list of section headings for the final report

User question: {request.user_query}

Return only valid JSON. No markdown fences."""

        try:
            response = await _llm.ainvoke([HumanMessage(content=prompt)])
            plan = json.loads(response.content)
        except Exception as exc:
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        return planner_pb2.PlanResponse(
            search_queries=plan.get("search_queries") or [request.user_query],
            report_sections=plan.get("report_sections") or [],
        )
```

---

## Walkthrough

### Step 1: The gRPC server starts

When the container launches, `asyncio.run(serve())` runs. It:
1. Creates a `grpc.aio.server()` — an async gRPC server
2. Registers `PlannerServicer()` so the framework knows which class handles `CreatePlan` calls
3. Opens port 50051 on all network interfaces (`[::]`)
4. Calls `wait_for_termination()` — blocks forever until Docker stops the container

### Step 2: The orchestrator calls `CreatePlan`

When the LangGraph `plan_research` node runs, it opens a gRPC channel to `planner-agent:50051` and calls `CreatePlan`. The framework deserializes the binary payload into a `PlanRequest` Python object and calls your `CreatePlan(request, context)` method.

### Step 3: The LLM generates a plan

The prompt asks the configured OpenRouter model (`z-ai/glm-4.5-air:free` by default, temperature=0 for determinism) to return **JSON** with two keys:
- `search_queries` — 3-5 specific queries to send to the search agent
- `report_sections` — headings for the final report

Example LLM output:
```json
{
  "search_queries": [
    "quantum computing basics 2024",
    "quantum algorithms applications",
    "quantum computing vs classical computing"
  ],
  "report_sections": [
    "Introduction",
    "How Quantum Computers Work",
    "Current Applications",
    "Future Outlook"
  ]
}
```

### Step 4: Build and return the response

`json.loads()` parses the LLM output. The `.get(...) or [request.user_query]` fallback ensures `search_queries` is never empty — if the LLM returns nothing, we at least search the original user question.

---

## Workflow

```
Orchestrator                    Planner Agent (port 50051)
────────────                    ──────────────────────────
plan_research node runs
  → create_plan(task_id, query)
  → open channel to planner-agent:50051
  → stub.CreatePlan(PlanRequest)  ──────►  PlannerServicer.CreatePlan()
                                            → build prompt
                                            → await _llm.ainvoke(prompt)
                                            → json.loads(response.content)
                                            → return PlanResponse(
                                                search_queries=[...],
                                                report_sections=[...]
                                              )
  ◄─────────── response ──────────────────
  → list(response.search_queries) → stored in state["research_plan"]
  → list(response.report_sections) → stored in state["report_sections"]
```

> [!tip]
> `temperature=0` makes the LLM deterministic — given the same question it returns the same plan every time. This is important for debugging: if the workflow fails, you can rerun and get the same plan to reproduce the issue.

> [!note]
> The `task_id` field is passed through in every gRPC request but the planner doesn't use it. It's there for future observability — when we add tracing in Phase 4, every gRPC call will include the task_id so we can trace a single research run across all services.

---

## Testing with grpcurl

```bash
# List available services
grpcurl -plaintext localhost:50051 list

# Call CreatePlan manually
grpcurl -plaintext \
  -d '{"task_id": "test-123", "user_query": "What is quantum computing?"}' \
  localhost:50051 planner.PlannerService/CreatePlan
```
