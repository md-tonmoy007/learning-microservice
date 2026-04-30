---
tags: [observability, opentelemetry, tracing]
---

# 10 OpenTelemetry Fundamentals

> OpenTelemetry is how this repo gives one request a shared identity across services.

Related: [[11 Tempo and the OTel Collector]] · [[OpenTelemetry]] · [[Home]]

---

## Trace and Span

A trace represents one end-to-end operation. A span represents one unit of work inside it.

For this repo, one trace might include:

- `POST /research` in the gateway
- work inside the orchestrator
- planner gRPC call
- search gRPC call
- summarizer gRPC call
- critic gRPC call
- report generation gRPC call

That span tree explains latency in a way logs alone cannot.

## Context Propagation

The essential trick is that child services receive the same trace context from parent services.

That is what lets Tempo draw one tree instead of seven disconnected events.

## Why OpenTelemetry Is a Good Fit

It is vendor-neutral, works across HTTP and gRPC, and supports automatic instrumentation for the frameworks used in this repo.
