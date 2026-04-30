---
tags: [phase-4, opentelemetry, tracing, grpc, fastapi, tempo]
file: services/orchestrator/app/core/telemetry.py
---

# 06 OpenTelemetry Tracing

> Every service calls `setup_telemetry()` at startup. That one function wires a TracerProvider that auto-instruments FastAPI HTTP requests and gRPC calls, and ships the resulting spans to the OTel Collector, which forwards them to Grafana Tempo.

Related: [[OpenTelemetry]] · [[01 Observability Overview]] · [[05 Loki and Promtail]] · [[Home]]

---

## The Code

### `core/telemetry.py` (identical in all seven services)

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(service_name: str, endpoint: str) -> None:
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    )
    trace.set_tracer_provider(provider)
```

### FastAPI services — `app/main.py` (api-gateway and orchestrator)

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorClient
from app.core.telemetry import setup_telemetry

setup_telemetry("orchestrator", settings.otel_endpoint)
GrpcAioInstrumentorClient().instrument()   # orchestrator only — it makes gRPC calls

# ... after app = FastAPI(...)
FastAPIInstrumentor.instrument_app(app)
```

### gRPC services — `app/main.py` (all five agents)

```python
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer
from app.core.telemetry import setup_telemetry

setup_telemetry("planner-agent", settings.otel_endpoint)
GrpcAioInstrumentorServer().instrument()

# ... asyncio.run(serve()) as before
```

### OTel Collector (`config/otel-collector.yaml`)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  otlp:
    endpoint: tempo:4317
    tls:
      insecure: true
  debug:
    verbosity: basic

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlp, debug]
```

### Grafana Tempo (`config/tempo.yaml`)

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks
    wal:
      path: /tmp/tempo/wal
```

---

## Walkthrough

### What a trace is

A **trace** is a record of one logical operation from start to finish. A **span** is one unit of work within that trace. Spans form a tree: the HTTP request is the root span, and every downstream call is a child.

```
Trace for "POST /research" (one research task):

[root span]  POST /research  (api-gateway, 31.2s total)
  [child]    POST /internal/research  (orchestrator HTTP, 31.1s)
    [child]  /planner.PlannerService/CreatePlan  (gRPC, 1.2s)
    [child]  /search.SearchService/Search  (gRPC, 4.1s)
    [child]  /search.SearchService/Search  (gRPC, 3.8s)   ← second iteration
    [child]  /summarizer.SummarizerService/Summarize  (gRPC, 6.4s)
    [child]  /critic.CriticService/Critique  (gRPC, 2.1s)
    [child]  /report.ReportService/GenerateReport  (gRPC, 13.5s)
```

Every span knows its parent. Grafana Tempo renders the full tree with timing bars, showing exactly where the 31 seconds went.

### Context propagation — how spans know their parent

When the orchestrator calls a gRPC agent, the OTel instrumentation automatically injects the current trace context into the gRPC metadata headers (W3C `traceparent` format):

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
              │  ├────────────── trace-id ──────────────┤ ├─ span-id ─┤ │
              │                                                         └─ flags
              └─ version
```

The agent's `GrpcAioInstrumentorServer` reads this header, creates a child span with the same `trace-id`, and records it. All spans with the same `trace-id` belong to the same trace.

Without context propagation, each service would generate isolated spans with no parent-child relationship — you'd see fragments, not a tree.

### `setup_telemetry` — what each line does

```python
resource = Resource.create({"service.name": service_name})
```
A Resource describes *what* is generating the spans. `service.name` is the key field — it's how Tempo and Grafana know which service each span came from. Without it, all spans appear as "unknown".

```python
provider = TracerProvider(resource=resource)
```
The TracerProvider is the factory for `Tracer` objects. There is one per process. The global one (`trace.set_tracer_provider(provider)`) is used by all OTel instrumentors.

```python
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
)
```
`OTLPSpanExporter` sends spans to the collector over gRPC (OTLP protocol). `BatchSpanProcessor` buffers spans in memory and sends them in batches — one network call per batch instead of one per span. This is critical for performance; without batching, every gRPC call would trigger its own export request.

```python
trace.set_tracer_provider(provider)
```
Sets the global tracer provider. All subsequent `trace.get_tracer()` calls (used internally by the instrumentors) get spans recorded to this provider.

### `GrpcAioInstrumentorClient` vs `GrpcAioInstrumentorServer`

| | Client | Server |
|--|--------|--------|
| Used in | orchestrator | planner, search, summarizer, critic, report |
| What it instruments | outgoing gRPC calls | incoming gRPC calls |
| Where spans appear | as children of the HTTP request span | as children of the gRPC client span |
| Propagates context | injects `traceparent` into outgoing metadata | extracts `traceparent` from incoming metadata |

The orchestrator calls `.instrument()` on the **client** because it makes outgoing gRPC calls. Each agent calls `.instrument()` on the **server** because it receives incoming gRPC calls.

### Module-level setup — why not in lifespan

```python
# Called at module import time, before the event loop starts
setup_telemetry("orchestrator", settings.otel_endpoint)
GrpcAioInstrumentorClient().instrument()

# FastAPI app created after
app = FastAPI(...)
FastAPIInstrumentor.instrument_app(app)
```

`GrpcAioInstrumentorClient().instrument()` patches the `grpc.aio` channel class globally. This must happen before any gRPC channel is created — including inside `lifespan()`. Calling it at module import time (before FastAPI even starts) guarantees correct ordering.

`setup_telemetry()` must also run before any OTel instrumentor tries to get a tracer, so module-level is correct there too.

---

## Workflow

```
Startup (every service):
  setup_telemetry("api-gateway", "http://otel-collector:4317")
    → TracerProvider created, BatchSpanProcessor started
    → OTLPSpanExporter pointing at otel-collector:4317

POST /research (user submits a query):
  → FastAPIInstrumentor creates root span: "POST /research" (api-gateway)
  → span context propagated in HTTP headers to orchestrator
  → FastAPIInstrumentor creates child span: "POST /internal/research" (orchestrator)
  → GrpcAioInstrumentorClient creates child span: "/planner.PlannerService/CreatePlan"
    → GrpcAioInstrumentorServer creates child span in planner-agent
    → planner-agent work completes → span ends
  → back in orchestrator → next gRPC call → child span ...

BatchSpanProcessor (every ~5s or 512 spans):
  → exports batch to otel-collector:4317 (OTLP gRPC)
  → otel-collector forwards to tempo:4317
  → Tempo stores the trace

Grafana → Explore → Tempo:
  → Search for traces by service name or trace ID
  → Click trace → see full span tree with timing bars
  → Click "Logs for this span" → jumps to Loki filtered by trace ID
```

> [!note]
> If the OTel Collector is down, spans queue in the `BatchSpanProcessor` buffer and are dropped when the buffer fills. The service itself continues working — tracing is non-blocking. You lose observability data but not production functionality.

> [!tip]
> To find a trace ID: look for `traceparent` in a log line (if you add it to the JSON logger), or submit a request and search Tempo by service name + time range. The Tempo "Search" tab lets you filter by `service.name`, duration, and status code without knowing the trace ID in advance.
