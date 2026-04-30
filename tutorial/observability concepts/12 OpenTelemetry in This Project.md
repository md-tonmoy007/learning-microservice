---
tags: [observability, opentelemetry, project, fastapi, grpc]
file: services/orchestrator/app/core/telemetry.py
---

# 12 OpenTelemetry in This Project

> The repo uses automatic instrumentation to create spans at the HTTP and gRPC boundaries with very little application code.

Related: [[13 Debugging with the Full Observability Stack]] · [[06 OpenTelemetry Tracing]] · [[Home]]

---

## Shared Setup

The common telemetry setup lives in [`services/orchestrator/app/core/telemetry.py`](/d:/learning-microservice/services/orchestrator/app/core/telemetry.py:1) and matching files in the other services.

It creates:

- a `TracerProvider`
- a `Resource` with `service.name`
- a `BatchSpanProcessor`
- an `OTLPSpanExporter`

## HTTP Instrumentation

The HTTP services call `FastAPIInstrumentor.instrument_app(app)`.

That means:

- incoming HTTP requests become spans automatically
- the gateway and orchestrator both appear in traces

## gRPC Instrumentation

The orchestrator instruments outgoing gRPC calls with `GrpcAioInstrumentorClient`.

Each agent instruments incoming gRPC calls with `GrpcAioInstrumentorServer`.

That pairing is what turns one request into a proper cross-service trace.

## One Useful Thing to Notice

The shared JSON logger does not currently include trace IDs. So traces and logs both exist, but trace-to-log correlation is not yet as rich as it could be. That is a good next improvement area if you keep expanding Phase 4.
