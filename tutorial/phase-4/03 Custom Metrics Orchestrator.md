---
tags: [phase-4, prometheus, metrics, orchestrator, langgraph]
file: services/orchestrator/app/services/research.py
---

# 03 Custom Metrics Orchestrator

> The orchestrator adds two custom Prometheus metrics — a Counter for task outcomes and a Histogram for end-to-end workflow duration — wired directly into `run_workflow`.

Related: [[Prometheus]] · [[02 Prometheus Metrics]] · [[04 Grafana Dashboards]] · [[Home]]

---

## The Code

`services/orchestrator/app/services/research.py` — additions at the top of the file:

```python
import time

from prometheus_client import Counter, Histogram

research_tasks_total = Counter(
    "research_tasks_total",
    "Total research tasks by final status",
    ["status"],
)
llm_workflow_duration_seconds = Histogram(
    "llm_workflow_duration_seconds",
    "End-to-end LangGraph workflow duration in seconds",
)
```

Inside `run_workflow` — the start and both exit paths:

```python
async def run_workflow(task_id: str, query: str) -> None:
    research_tasks_total.labels(status="started").inc()   # ← task starts
    start_time = time.monotonic()
    async with AsyncSessionFactory() as db:
        ...
        try:
            # LangGraph runs here
            ...
            research_tasks_total.labels(status="completed").inc()          # ← success
            llm_workflow_duration_seconds.observe(time.monotonic() - start_time)
            ...

        except Exception as exc:
            ...
            research_tasks_total.labels(status="failed").inc()             # ← failure
            llm_workflow_duration_seconds.observe(time.monotonic() - start_time)
```

---

## Walkthrough

### Counter vs Histogram — which to use

**Counter** — a value that only ever goes up. Use it to count events: tasks started, tasks completed, tasks failed, errors, retries. You almost always use `rate()` or `increase()` in PromQL to turn a counter into a rate.

**Histogram** — records how long something took (or how big it was), split into configurable buckets. Use it for durations and sizes. It gives you percentiles.

**Gauge** — a value that goes up and down. Use it for current state: number of active connections, queue depth, memory used. Not used here because task count and duration are cumulative, not current-state.

### The `labels` pattern

```python
research_tasks_total = Counter("research_tasks_total", "...", ["status"])

# Calling .labels(status="started") creates a child counter for that label combination.
research_tasks_total.labels(status="started").inc()
research_tasks_total.labels(status="completed").inc()
research_tasks_total.labels(status="failed").inc()
```

In Prometheus, one metric with labels becomes multiple time series:

```
research_tasks_total{status="started"}   42
research_tasks_total{status="completed"} 38
research_tasks_total{status="failed"}    4
```

This lets you ask: "what fraction of started tasks failed?" with a single PromQL expression rather than separate metrics.

### `time.monotonic()` — not `time.time()`

`time.monotonic()` returns seconds since an arbitrary fixed point that only increases. It's immune to system clock adjustments (NTP, daylight saving, manual changes). Always use it for measuring durations.

`time.time()` can jump forwards or backwards, which would corrupt duration measurements.

```python
start_time = time.monotonic()
# ... work happens ...
duration = time.monotonic() - start_time   # always positive, always accurate
```

### Why track "started" separately from "completed" + "failed"

The difference `started - (completed + failed)` is the number of currently in-flight tasks. If that number grows over time, tasks are being submitted faster than they finish — a capacity problem. This is more reliable than a Gauge (which requires you to remember to decrement it on every exit path).

In PromQL:
```promql
increase(research_tasks_total{status="started"}[1h])
- increase(research_tasks_total{status="completed"}[1h])
- increase(research_tasks_total{status="failed"}[1h])
```

### Where these metrics appear

After `Instrumentator().instrument(app).expose(app)` is called in `main.py`, the `prometheus_client` default registry (which holds all `Counter` and `Histogram` instances) is exposed at `GET /metrics` automatically. No extra wiring needed — `prometheus-fastapi-instrumentator` uses the same default registry as `prometheus-client`.

```
GET orchestrator:8001/metrics

# HELP research_tasks_total Total research tasks by final status
# TYPE research_tasks_total counter
research_tasks_total_total{status="started"} 5.0
research_tasks_total_total{status="completed"} 4.0
research_tasks_total_total{status="failed"} 1.0

# HELP llm_workflow_duration_seconds End-to-end LangGraph workflow duration in seconds
# TYPE llm_workflow_duration_seconds histogram
llm_workflow_duration_seconds_bucket{le="0.005"} 0.0
llm_workflow_duration_seconds_bucket{le="0.01"} 0.0
...
llm_workflow_duration_seconds_bucket{le="+Inf"} 5.0
llm_workflow_duration_seconds_sum 187.42
llm_workflow_duration_seconds_count 5.0
```

---

## Workflow

```
Orchestrator receives "research.created" event:
  run_workflow("abc-123", "What is quantum computing?")
    → research_tasks_total.labels("started").inc()     [counter: started=1]
    → start_time = time.monotonic()
    → LangGraph runs (30 seconds)
    → research_tasks_total.labels("completed").inc()   [counter: completed=1]
    → llm_workflow_duration_seconds.observe(30.1)      [histogram: one sample at 30.1s]

Prometheus scrapes 15s later:
  GET orchestrator:8001/metrics
    → research_tasks_total{status="started"} 1
    → research_tasks_total{status="completed"} 1
    → llm_workflow_duration_seconds_count 1
    → llm_workflow_duration_seconds_sum 30.1

Grafana dashboard panel (PromQL):
  histogram_quantile(0.99, rate(llm_workflow_duration_seconds_bucket[10m]))
    → "p99 workflow duration over last 10 minutes"
```

> [!tip]
> The `_total` suffix you see in the raw output (`research_tasks_total_total`) is added automatically by `prometheus_client`. The metric is named `research_tasks_total` in code; Prometheus appends `_total` to all Counter names by convention. In PromQL you query it as `research_tasks_total_total` — or just use `increase(research_tasks_total_total[5m])`.
