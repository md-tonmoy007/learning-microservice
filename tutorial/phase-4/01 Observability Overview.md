---
tags: [phase-4, observability, prometheus, loki, opentelemetry, grafana]
file: docker-compose.yml
---

# 01 Observability Overview

> Phase 4 makes the system observable: every service exposes metrics, every log is searchable, and every request leaves a trace that spans all seven services.

Related: [[Prometheus]] · [[OpenTelemetry]] · [[Grafana]] · [[Home]]

---

## The Problem with Phase 3

After Phase 3, the system works. Research tasks are submitted, LangGraph runs, Kafka carries events, the browser gets a live stream. But when something is slow or broken you can only ask one question: "did it fail?"

You cannot answer:
- Why did the 14:30 research task take 45 seconds when the 14:15 task took 8 seconds?
- Which gRPC agent is the slowest?
- The orchestrator returned `status: failed` — which LangGraph node failed and what was the error?
- How many tasks have failed in the last hour? Is the failure rate increasing?

To answer these you need **observability** — the ability to understand internal system state by examining its external outputs.

---

## The Three Pillars

Observability has three complementary signals. Each answers a different type of question.

| Pillar | Tool | Answers | Example question |
|--------|------|---------|-----------------|
| **Metrics** | Prometheus + Grafana | *How many? How fast? How often?* | "What is the p99 latency of `POST /research`?" |
| **Logs** | Loki + Promtail + Grafana | *What happened, in what order?* | "Show me all log lines for task `abc-123`" |
| **Traces** | OpenTelemetry + Tempo + Grafana | *Where did the time go across services?* | "Show the full span tree for request `abc-123`" |

They are most powerful together. A Grafana dashboard shows a spike in p99 latency (metric). You click the spike, find a trace that shows the `summarize_results` gRPC call took 30 seconds. You pivot to Loki and filter logs for that trace ID — "LLM rate limited, retrying in 20s" (log). Three questions answered in under a minute.

---

## What Phase 4 Changes

### Every FastAPI service gains

```
Before Phase 4:              After Phase 4:
  /health     (exists)         /health     (unchanged)
  /metrics    (missing)        /metrics    (Prometheus scrapes this every 15s)
  logs → stdout only           logs → Promtail → Loki (searchable)
  no tracing                   every HTTP request has OTel spans
```

### Every gRPC service gains

```
Before Phase 4:              After Phase 4:
  logs → stdout only           logs → Promtail → Loki
  no tracing                   every gRPC call has OTel spans
```

### docker-compose gains six new services

| Service | Port | Role |
|---------|------|------|
| `prometheus` | 9090 | Scrapes `/metrics` from api-gateway and orchestrator |
| `grafana` | 3000 | Dashboard UI — queries Prometheus, Loki, Tempo |
| `loki` | 3100 | Stores and indexes structured logs |
| `promtail` | — | Reads Docker container logs, ships to Loki |
| `otel-collector` | 4317 | Receives OTel spans from all services, exports to Tempo |
| `tempo` | 3200 | Stores distributed traces |

---

## The Phase 4 Data Flow

```
Every HTTP request (api-gateway, orchestrator):
  FastAPIInstrumentor → OTel root span → BatchSpanProcessor → otel-collector:4317 → Tempo

Every gRPC call (orchestrator → agents):
  GrpcAioInstrumentorClient → child OTel span → same pipeline

Every gRPC handler (planner, search, summarizer, critic, report):
  GrpcAioInstrumentorServer → child OTel span → same pipeline

Every 15 seconds:
  Prometheus → GET api-gateway:8000/metrics
  Prometheus → GET orchestrator:8001/metrics

Continuously:
  Promtail → reads /var/run/docker.sock → ships container stdout → Loki

Grafana:
  datasource Prometheus → PromQL dashboards
  datasource Loki       → LogQL log explorer
  datasource Tempo      → trace viewer with log correlation
```

---

## Why All Three? Aren't Logs Enough?

**Logs alone cannot answer metric questions.** To find p99 request latency over the last hour you'd need to parse every log line, extract timestamps, and compute percentiles yourself. Prometheus stores pre-aggregated time series — p99 is two PromQL lines.

**Logs alone cannot answer trace questions.** A request that touches 7 services leaves logs spread across 7 log streams. Finding all of them requires knowing the exact `task_id` and searching each stream separately. A trace links them all under one root span with timing you can see at a glance.

**Metrics alone cannot answer debugging questions.** A metric tells you *that* p99 latency spiked. It doesn't tell you *which specific request* was slow or *why*. Traces and logs fill that gap.

---

## Read Order

Work through Phase 4 notes in this sequence:

1. [[02 Prometheus Metrics]] — add `/metrics` to the FastAPI services, understand what you get for free, how Prometheus scrapes
2. [[03 Custom Metrics Orchestrator]] — add `research_tasks_total` and `llm_workflow_duration_seconds` counters to `run_workflow`
3. [[04 Grafana Dashboards]] — connect Grafana to Prometheus, write your first PromQL queries, open the dashboards
4. [[05 Loki and Promtail]] — ship container logs to Loki, query them with LogQL in Grafana
5. [[06 OpenTelemetry Tracing]] — instrument every service, run the OTel Collector, view full request traces in Grafana Tempo

> [!tip]
> You can implement and verify each layer independently. After step 02: open `localhost:9090` in Prometheus and see metrics. After step 04: open `localhost:3000` in Grafana and see dashboards. After step 05: search logs. After step 06: view end-to-end traces.
