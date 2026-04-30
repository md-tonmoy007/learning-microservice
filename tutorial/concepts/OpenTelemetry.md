---
tags: [concept, opentelemetry, tracing, observability, grpc]
---

# OpenTelemetry

> OpenTelemetry (OTel) is a vendor-neutral standard for collecting traces, metrics, and logs. In this project it instruments FastAPI and gRPC automatically, producing spans that Grafana Tempo assembles into full request traces.

Used in: [[06 OpenTelemetry Tracing]] · [[01 Observability Overview]]

---

## The Core Idea

Without OTel, a request that touches 7 services leaves behind 7 disconnected log files. You know each service did something, but you can't see the full picture: how long each step took, which step was slow, how they relate.

OTel attaches a **trace ID** to every request at the entry point. Every downstream call carries that same ID. At the end you have one trace: a tree of spans, each timed, each labeled with the service that produced it.

```
Trace abc-123:
  [api-gateway]      POST /research          0ms → 31,200ms
    [orchestrator]   POST /internal/research  5ms → 31,195ms
      [planner]      CreatePlan             10ms → 1,210ms
      [search]       Search              1,215ms → 5,315ms
      [search]       Search              5,320ms → 9,120ms
      [summarizer]   Summarize           9,125ms → 15,525ms
      [critic]       Critique           15,530ms → 17,630ms
      [report]       GenerateReport     17,635ms → 31,135ms
```

---

## Key Concepts

**Trace** — one end-to-end operation, identified by a `trace-id` (128-bit random hex). All spans with the same `trace-id` belong to the same trace.

**Span** — one unit of work. Has a name, start time, duration, status, and optional attributes. Each span knows its parent span ID.

**Context propagation** — the mechanism that passes the trace ID from service to service. In HTTP: the `traceparent` header. In gRPC: metadata. The OTel instrumentors inject and extract these automatically.

**TracerProvider** — the factory for Tracer objects. One per process. Set globally with `trace.set_tracer_provider(provider)`.

**Exporter** — sends finished spans to a backend. `OTLPSpanExporter` sends to any OTLP-compatible collector over gRPC.

**BatchSpanProcessor** — buffers spans in memory and exports them in batches. More efficient than exporting one span at a time.

**OTel Collector** — a standalone process that receives spans from services (OTLP gRPC on `:4317`), can transform them, and exports to one or more backends (Tempo, Jaeger, Zipkin, cloud vendors). Services talk to the collector, not the backend directly — a single config change in the collector reroutes all spans.

---

## The SDK Components

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# 1. Describe this service
resource = Resource.create({"service.name": "my-service"})

# 2. Create provider
provider = TracerProvider(resource=resource)

# 3. Wire exporter via batch processor
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
)

# 4. Register globally
trace.set_tracer_provider(provider)
```

---

## Auto-instrumentation vs Manual

**Auto-instrumentation** (used in this project):
```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorClient, GrpcAioInstrumentorServer

FastAPIInstrumentor.instrument_app(app)     # every HTTP request → a span
GrpcAioInstrumentorClient().instrument()   # every outgoing gRPC call → a span
GrpcAioInstrumentorServer().instrument()   # every incoming gRPC call → a span
```
Zero code changes to route handlers or servicers. The instrumentors monkey-patch the frameworks.

**Manual instrumentation** (for custom spans inside functions):
```python
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("my-operation") as span:
    span.set_attribute("task_id", task_id)
    do_work()
```
Use manual spans when auto-instrumentation doesn't cover a specific function you want to time.

---

## The Collector Pipeline

```
service                 otel-collector          tempo
   │                         │                    │
   ├─ OTLP gRPC spans ──────►│                    │
   │  (port 4317)            ├─ OTLP gRPC ───────►│
   │                         │  (port 4317)        │
   │                         ├─ debug log          │
   │                         │  (to stdout)        │
```

The collector config (`config/otel-collector.yaml`):
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  otlp:
    endpoint: tempo:4317
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlp]
```

The collector decouples services from backends. You can add a second exporter (e.g. send to a cloud tracing service) by adding one line to the collector config — no service code changes.

---

## W3C Trace Context — the `traceparent` header

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

| Field | Value | Meaning |
|-------|-------|---------|
| version | `00` | W3C spec version |
| trace-id | `4bf9...4736` | 128-bit, identifies the whole trace |
| parent-id | `00f0...02b7` | 64-bit, this span's ID (becomes the parent for the next hop) |
| flags | `01` | sampling flag (01 = sampled) |

OTel auto-instrumentation injects this header into every outgoing HTTP request and gRPC call. On the receiving end, it extracts it and creates the child span with the correct parent ID.

> [!tip]
> Add `trace_id` to your structured JSON logs by reading `trace.get_current_span().get_span_context().trace_id` and including it in the log payload. Then Grafana's "trace to logs" correlation works automatically — clicking a span in Tempo jumps to Loki filtered by that trace ID.
