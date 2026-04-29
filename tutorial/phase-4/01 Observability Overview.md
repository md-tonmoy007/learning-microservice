---
tags: [phase-4, observability, prometheus, loki, opentelemetry, grafana]
file: docker-compose.yml
---

# 01 Observability Overview

> Phase 4 makes the system observable: every service exposes metrics, every log is searchable, and every request leaves a trace that spans all seven services.

Related: [[Prometheus]] · [[OpenTelemetry]] · [[Grafana]] · [[Home]]

---

## The Problem with Phase 3

After Phase 3, the system works. Research tasks are submitted, LangGraph runs, Kafka carries events, the browser gets a live stream. But you can only answer one question when something goes wrong: "did it fail?" You can't answer:

- Why did the 14:30 research task take 45 seconds when the 14:15 task took 8 seconds?
- Which gRPC agent is the slowest?
- The orchestrator returned `status: failed` — which node failed and what was the error?
- How many tasks have failed in the last hour? Is the failure rate increasing?

To answer these, you need **observability** — the ability to understand the internal state of a system by examining its external outputs.

---

## The Three Pillars

Observability has three complementary signals. Each answers a different type of question.

| Pillar | Tool | Answers | Example question |
|--------|------|---------|-----------------|
| **Metrics** | Prometheus + Grafana | *How many? How fast? How often?* | "What is the p99 latency of `POST /research`?" |
| **Logs** | Loki + Promtail + Grafana | *What happened, in what order?* | "Show me all log lines for task `abc-123`" |
| **Traces** | OpenTelemetry + Tempo + Grafana | *Where did the time go across services?* | "Show the full span tree for request `abc-123`" |

These three signals are most powerful together. A Grafana dashboard shows a spike in p99 latency (metric). You click the spike and see a trace that shows the `summarize_results` gRPC call took 30 seconds. You click into the summarizer-agent service logs filtered to that trace ID and see "LLM rate limited, retrying in 20s" (log).

---

## What Phase 4 Adds

### To every service

```
Before Phase 4:                After Phase 4:
  /health     (exists)           /health     (unchanged)
  /metrics    (missing)          /metrics    (Prometheus scrapes this)
  logs → stdout only             logs → stdout + Promtail → Loki
  no tracing                     every request has a trace ID
```

### To docker-compose.yml

Five new infrastructure services are added:

```
Prometheus  (:9090)  — scrapes /metrics from every service every 15s
Grafana     (:3000)  — dashboards for Prometheus, Loki, Tempo
Loki        (:3100)  — stores and indexes structured logs
Promtail             — reads Docker container logs, ships to Loki
OTel Collector       — receives spans from all services, exports to Tempo
Tempo       (:3200)  — stores distributed traces
```

---

## The Phase 4 Architecture

```
Every HTTP request:
  api-gateway → FastAPIInstrumentor → OTel span + W3C headers
                ↓
  orchestrator → FastAPIInstrumentor → child OTel span
                ↓
  each gRPC call → GrpcAioInstrumentorClient → child OTel span

Every 15 seconds:
  Prometheus → scrape → /metrics (api-gateway)
  Prometheus → scrape → /metrics (orchestrator)
  Prometheus → scrape → /metrics (planner-agent, search-agent, ...)

Continuously:
  Promtail → read Docker container logs → ship to Loki
  Services → OTLP spans → OTel Collector → Grafana Tempo

Grafana:
  datasource: Prometheus → PromQL dashboards
  datasource: Loki       → LogQL log explorer
  datasource: Tempo      → trace viewer
```

---

## Why All Three? Not Just Logs?

It's tempting to say "I already have logs, why do I need metrics or traces?"

**Logs alone are not enough for metrics.** To answer "what is the p99 request latency over the last hour?", you'd have to read every log line, parse timestamps, and compute percentiles. Prometheus stores pre-aggregated metric time series specifically for this. Querying p99 latency is two PromQL lines, not a log processing pipeline.

**Logs alone are not enough for tracing.** When a request touches 7 services, the logs for that request are spread across 7 different log streams. Finding them all requires knowing the exact `task_id` and searching each service's logs separately. A trace links them all under one root span with timing, so you see the full picture in one view.

**Metrics alone are not enough for debugging.** A metric tells you *that* p99 latency spiked. It doesn't tell you *which specific request* was slow or *why*. Traces and logs fill that gap.

---

## Read Order

Work through the Phase 4 notes in this sequence:

1. [[02 Prometheus Metrics]] — add `/metrics` to all services, wire up Prometheus scraping, understand what you get for free
2. [[03 Custom Metrics Orchestrator]] — add `research_tasks_total`, `llm_latency_seconds`, and `agent_calls_total` to the orchestrator
3. [[04 Grafana Dashboards]] — connect Grafana to Prometheus, write PromQL, build the six dashboards
4. [[05 Loki and Promtail]] — ship container logs to Loki, query them with LogQL in Grafana
5. [[06 OpenTelemetry Tracing]] — instrument every service, run the OTel Collector, view full request traces in Grafana Tempo

> [!tip]
> You can implement these in order and test each layer before moving to the next. After note 02, you can already open Prometheus at `localhost:9090` and see metrics. After note 03, you can see custom counters. After note 04, you have dashboards. After note 05, you can search logs. After note 06, you have full distributed traces.
