---
tags: [concept, grpc, protobuf, serialization]
---

# Protocol Buffers

> Protocol Buffers define the typed contracts between services. A `.proto` file is the source of truth; Python stubs are always derived from it.

Used in: [[gRPC Agent Decomposition]] · [[Planner Agent]] · [[Search Agent]] · [[Summarizer Agent]] · [[Critic Agent]] · [[Report Service]] · [[gRPC Clients]]

---

## What Is a `.proto` File?

A `.proto` file describes two things:

1. **Messages** — the data structures passed between services (like Python dataclasses)
2. **Services** — the RPC methods that can be called (like function signatures)

Example from `proto/planner.proto`:
```proto
syntax = "proto3";
package planner;

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

Reading this like English: "The `PlannerService` exposes a method called `CreatePlan`. It accepts a `PlanRequest` (which has a task_id and user_query) and returns a `PlanResponse` (which has lists of search queries and section headings)."

---

## Field Types

| Proto type | Python type | Example usage |
|------------|-------------|---------------|
| `string` | `str` | task_id, user_query, summary |
| `int32` | `int` | count, page number |
| `float` | `float` | score (0.0–1.0) |
| `bool` | `bool` | needs_more_research |
| `bytes` | `bytes` | raw binary data |
| `repeated T` | `list[T]` | search_queries, results |
| `MessageType` | object | nested message |

`repeated` is the protobuf keyword for "a list of". In Python it becomes a list:
```python
# proto: repeated string search_queries = 1;
response.search_queries   # → a list of strings in Python
list(response.search_queries)  # convert to plain Python list
```

---

## Field Numbers

Every field has a number (`= 1`, `= 2`, etc.). These are **not positions** — they are stable identifiers used in the binary encoding:

```proto
message PlanRequest {
  string task_id = 1;    // field number 1
  string user_query = 2; // field number 2
}
```

> [!warning]
> Never change a field number once the service is in production. Changing a field number breaks binary compatibility — existing messages encoded with the old number cannot be decoded with the new one. You can add new fields (new numbers) or delete old fields, but never renumber.

---

## The Five Proto Files in This Project

| File | Service | Key Messages |
|------|---------|-------------|
| `proto/planner.proto` | PlannerService | PlanRequest → PlanResponse |
| `proto/search.proto` | SearchService | SearchRequest → SearchResponse (with SearchResult) |
| `proto/summarizer.proto` | SummarizerService | SummarizeRequest → SummarizeResponse |
| `proto/critic.proto` | CriticService | CritiqueRequest → CritiqueResponse |
| `proto/report.proto` | ReportService | ReportRequest → ReportResponse |

The `search.proto` is the most complex — it defines a nested `SearchResult` message that is reused inside both `SearchResponse` and `SummarizeRequest`:
```proto
message SearchResult {
  string title = 1;
  string url = 2;
  string content = 3;
  string source_type = 4;
}

message SearchResponse {
  repeated SearchResult results = 1;  // list of SearchResult objects
}
```

---

## Generating Python Stubs

After writing or editing a `.proto` file, run `grpc_tools.protoc` to generate Python code:

```bash
# Run from the workspace root
python -m grpc_tools.protoc \
  -I proto \
  --python_out=services/planner-agent/app/grpc_generated \
  --grpc_python_out=services/planner-agent/app/grpc_generated \
  proto/planner.proto
```

This creates two files per service:

| File                  | What it contains                                                        |     |
| --------------------- | ----------------------------------------------------------------------- | --- |
| `planner_pb2.py`      | Message classes: `PlanRequest`, `PlanResponse`                          |     |
| `planner_pb2_grpc.py` | `PlannerServiceServicer` base class + `PlannerServiceStub` client class |     |
|                       |                                                                         |     |
|                       |                                                                         |     |

You need to generate stubs for **both** the agent service (the gRPC server) and the orchestrator (the gRPC client) because both sides use the same message classes.

---

## Using Generated Message Classes

```python
from app.grpc_generated import planner_pb2

# Create a message
req = planner_pb2.PlanRequest(
    task_id="abc-123",
    user_query="What is quantum computing?",
)

# Access fields
print(req.task_id)     # "abc-123"
print(req.user_query)  # "What is quantum computing?"

# Create a response with repeated field
resp = planner_pb2.PlanResponse(
    search_queries=["quantum computing basics", "quantum algorithms"],
    report_sections=["Introduction", "Key Concepts"],
)

# repeated fields look like lists but are special protobuf types
# convert to plain Python list when needed
queries = list(resp.search_queries)
```

---

## Why Stubs Are Gitignored

Generated files (`app/grpc_generated/`) are in `.gitignore` because:

1. They are **derived** — always reproducible from the `.proto` source
2. Committing them creates merge conflicts with no meaningful diff
3. The generation command is documented in `CLAUDE.md` — anyone can regenerate

The `.proto` files in `proto/` are checked in — they are the human-editable source of truth.

> [!note]
> The `grpc_generated_path.py` utility in each service adds `app/grpc_generated/` to `sys.path` at runtime so the imports work even though the files aren't in a proper Python package with `__init__.py`.
