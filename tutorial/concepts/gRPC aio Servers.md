---
tags: [concept, grpc, async-python, asyncio]
---

# gRPC aio Servers

> `grpc.aio.server()` runs async Python gRPC services without blocking the event loop.

Used in: [[Planner Agent]] · [[Search Agent]] · [[Summarizer Agent]] · [[Critic Agent]] · [[Report Service]] · [[gRPC Agent Decomposition]]

---

## Why `grpc.aio` Instead of `grpc`?

The gRPC Python library has two APIs:

| API | How it works | Use when |
|-----|-------------|----------|
| `grpc.server()` | Spawns threads for each request | Legacy code, sync handlers |
| `grpc.aio.server()` | Uses asyncio event loop | Async handlers (this project) |

Every agent in this project uses `async def` for its RPC handler because LangChain's LLM calls and Tavily search are async (`await _llm.ainvoke(...)`, `await _search.ainvoke(...)`). Using `grpc.aio` means those awaits run on the same event loop without blocking.

---

## The Server Startup Pattern

Every agent's `app/main.py` follows the same three-step pattern:

```python
import asyncio
import grpc
from app.grpc_generated import planner_pb2_grpc
from app.services.planner import PlannerServicer

async def serve() -> None:
    # Step 1: Create an async gRPC server
    server = grpc.aio.server()

    # Step 2: Register the servicer (your handler class)
    planner_pb2_grpc.add_PlannerServiceServicer_to_server(PlannerServicer(), server)

    # Step 3: Bind a port and start
    server.add_insecure_port(f"[::]:{settings.grpc_port}")
    await server.start()

    # Keep running until the container stops
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
```

`[::]:50051` means "listen on all network interfaces, port 50051". The `::` is the IPv6 wildcard; gRPC maps it to both IPv4 and IPv6 automatically.

---

## The Servicer Class

The servicer is where your business logic lives. The generated `planner_pb2_grpc.py` defines a base class (`PlannerServiceServicer`) with stub methods you override:

```python
# In app/grpc_generated/planner_pb2_grpc.py (auto-generated, don't edit)
class PlannerServiceServicer:
    async def CreatePlan(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")
```

You subclass it and override the methods:
```python
# In app/services/planner.py (your code)
class PlannerServicer(planner_pb2_grpc.PlannerServiceServicer):
    async def CreatePlan(self, request, context):
        # request is a PlanRequest message
        # context lets you set status codes, metadata, etc.
        response = await _llm.ainvoke([...])
        return planner_pb2.PlanResponse(...)
```

The framework calls your `CreatePlan` method each time the orchestrator sends a request.

---

## The `context` Parameter

The second argument to every RPC handler is the `context` object. It gives you control over the response metadata and status:

```python
async def CreatePlan(self, request, context):
    # Abort — sends an error response immediately, no return value needed
    await context.abort(grpc.StatusCode.INTERNAL, "LLM unavailable")

    # Set response metadata (key-value pairs the client can read)
    await context.send_initial_metadata([("x-request-id", "abc")])

    # Read the deadline set by the client
    deadline = context.time_remaining()
```

**Important about `context.abort()`**: In `grpc.aio`, calling `await context.abort(...)` raises an internal exception that terminates the handler. The code after `context.abort()` does **not** execute. Adding `return` after abort is a safety habit — it signals your intent even though the abort already stops execution.

---

## Error Handling Pattern

Every agent catches exceptions and aborts with `INTERNAL` status:

```python
try:
    response = await _llm.ainvoke([HumanMessage(content=prompt)])
    parsed = json.loads(response.content)
except Exception as exc:
    await context.abort(grpc.StatusCode.INTERNAL, str(exc))
    return  # defensive — abort already raises, but explicit is clearer
```

On the client side (orchestrator), this `INTERNAL` error arrives as a `grpc.aio.AioRpcError` exception:
```python
try:
    response = await stub.CreatePlan(request)
except grpc.aio.AioRpcError as exc:
    raise RuntimeError(f"Planner gRPC failed: {exc.details()}") from exc
```

`exc.details()` returns the string you passed to `context.abort()` — the original error message from the agent service.

---

## Request Lifecycle

```
Container starts
  → asyncio.run(serve())
  → grpc.aio.server() created
  → PlannerServicer() registered
  → server.start() — port open, accepting connections
  → server.wait_for_termination() — event loop runs forever

Orchestrator sends CreatePlan RPC:
  → framework deserializes PlanRequest from binary
  → calls await PlannerServicer().CreatePlan(request, context)
  → your async handler runs (LLM call, JSON parse, etc.)
  → you return a PlanResponse
  → framework serializes it to binary and sends it back

Container receives SIGTERM (docker stop):
  → server gracefully drains in-flight requests
  → wait_for_termination() returns
  → process exits
```

> [!note]
> `grpc.aio` handles one request at a time on the same event loop, but because every handler awaits (non-blocking), many requests can be in-flight concurrently — just like FastAPI. If a handler did CPU-heavy work without yielding, it would block all other requests.
