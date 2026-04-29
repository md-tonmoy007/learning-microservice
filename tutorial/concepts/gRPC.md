---
tags: [concept, grpc, networking, microservices]
---

# gRPC

> gRPC is a framework for making function calls across a network as if calling a local function.

Used in: [[Planner Agent]] · [[Search Agent]] · [[Summarizer Agent]] · [[Critic Agent]] · [[Report Service]] · [[gRPC Clients]] · [[gRPC Agent Decomposition]]

---

## The Problem gRPC Solves

When services need to talk to each other over a network, you have to decide: what format does the request take? How does the other side know what fields to expect? What happens when something goes wrong?

With plain HTTP + JSON, you invent your own conventions. With gRPC you get all of that out of the box — typed contracts, binary encoding, and generated client code.

---

## The Core Idea

gRPC works in two parts:

**1. You define a contract in a `.proto` file:**
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
}
```

**2. A code generator turns that into Python (or Go, Java, etc.):**
```bash
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/planner.proto
```

This produces two files:
- `planner_pb2.py` — the message classes (`PlanRequest`, `PlanResponse`)
- `planner_pb2_grpc.py` — the server base class (`PlannerServiceServicer`) and client stub (`PlannerServiceStub`)

You never write these files by hand. You edit the `.proto` and regenerate.

---

## How a gRPC Call Works (Step by Step)

```
Client (orchestrator)                    Server (planner-agent)
─────────────────────                    ──────────────────────
1. Create PlanRequest(task_id, query)
2. Open channel to planner-agent:50051
3. Call stub.CreatePlan(request)  ──────► gRPC framework receives binary bytes
                                          4. Decode bytes → PlanRequest Python object
                                          5. Call PlannerServicer.CreatePlan(request, context)
                                          6. Run LLM, build PlanResponse
                                          7. Return PlanResponse  ◄──────────────
8. Decode response bytes
9. Access response.search_queries
```

The network layer is handled entirely by the gRPC framework. You just call what looks like a local function.

---

## gRPC vs REST

| Concern | gRPC | REST/HTTP+JSON |
|---------|------|----------------|
| Contract | `.proto` file — strongly typed, version controlled | OpenAPI spec — loosely enforced |
| Serialization | Protobuf binary — compact, fast | JSON text — readable but larger |
| Code generation | Auto-generates client + server stubs | Manual or openapi-generator |
| Streaming | First-class (4 modes built in) | Workarounds (SSE, WebSocket) |
| Error model | Rich status codes with details | HTTP status codes (coarser) |
| Browser support | Not natively (needs gRPC-web proxy) | Native |

For internal service-to-service calls like in this project, gRPC is the better fit. REST is easier when humans or browsers are the client.

---

## The Four Service Types

gRPC supports four calling patterns. This project uses only **Unary** (one request, one response):

```proto
// 1. Unary — one request, one response (what we use)
rpc CreatePlan (PlanRequest) returns (PlanResponse);

// 2. Server streaming — one request, stream of responses
rpc WatchResearch (TaskRequest) returns (stream StatusUpdate);

// 3. Client streaming — stream of requests, one response
rpc UploadDocuments (stream Document) returns (UploadResult);

// 4. Bidirectional streaming — stream both ways
rpc Chat (stream Message) returns (stream Message);
```

Streaming becomes useful in Phase 3 when we want to push live progress updates to the client.

---

## gRPC Status Codes

gRPC defines its own status codes, richer than HTTP's:

| Code | Meaning | When it appears |
|------|---------|-----------------|
| `OK` | Success | Normal response |
| `INTERNAL` | Server-side error | LLM call fails, JSON parse error |
| `UNAVAILABLE` | Service unreachable | Container not running, port wrong |
| `INVALID_ARGUMENT` | Bad request data | Missing required field |
| `DEADLINE_EXCEEDED` | Timeout | Service took too long |
| `NOT_FOUND` | Resource missing | ID doesn't exist |

In this project, every agent uses `INTERNAL` when anything unexpected happens:
```python
await context.abort(grpc.StatusCode.INTERNAL, str(exc))
```

The orchestrator catches these as `grpc.aio.AioRpcError` and converts them to `RuntimeError`.

---

## Insecure vs Secure Channels

All channels in this project are **insecure** — no TLS:
```python
grpc.aio.insecure_channel("planner-agent:50051")
```

This is fine inside a private Docker network where services trust each other. For public-facing gRPC (Phase 6 / Kubernetes Ingress), you would use `grpc.aio.secure_channel()` with TLS credentials.

---

## Why It Fits This Project

Each agent is a stateless worker that does one job. The orchestrator needs to call them with typed inputs and get typed outputs. gRPC gives:

- **Typed contracts** — proto files are the shared spec between orchestrator and agents
- **Generated clients** — no hand-writing HTTP request builders
- **Binary efficiency** — repeated across 5 agents per research run, every byte matters
- **Async support** — `grpc.aio` fits Python's asyncio model used throughout this stack

> [!tip]
> Think of gRPC as RPC (Remote Procedure Call) — calling a function that lives on another machine. The `.proto` file is the function signature. The generated stubs are the local wrapper that makes the network call feel like a function call.
