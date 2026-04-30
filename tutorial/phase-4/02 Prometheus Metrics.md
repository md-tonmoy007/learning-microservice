---
tags: [phase-4, prometheus, metrics, fastapi]
file: services/api-gateway/app/main.py
---

# 02 Prometheus Metrics

> Two lines of code add a `/metrics` endpoint to every FastAPI service. Prometheus scrapes it every 15 seconds and stores the time series you query in Grafana.

Related: [[Prometheus]] · [[01 Observability Overview]] · [[03 Custom Metrics Orchestrator]] · [[Home]]

---

## The Code

### Adding the instrumentator (api-gateway and orchestrator)

`services/api-gateway/app/main.py` and `services/orchestrator/app/main.py` both received the same two additions:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

# ... after app = FastAPI(...)

Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)
```

`Instrumentator().instrument(app)` registers a middleware that measures every request. `.expose(app)` mounts a `GET /metrics` route that returns the collected metrics in Prometheus text format.

### New packages (pyproject.toml)

**api-gateway:**
```toml
"prometheus-fastapi-instrumentator>=7.0.0",
"opentelemetry-sdk>=1.20.0",
"opentelemetry-instrumentation-fastapi>=0.40b0",
"opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
```

**orchestrator** (adds `prometheus-client` for custom metrics):
```toml
"prometheus-fastapi-instrumentator>=7.0.0",
"prometheus-client>=0.20.0",
"opentelemetry-sdk>=1.20.0",
"opentelemetry-instrumentation-fastapi>=0.40b0",
"opentelemetry-instrumentation-grpc>=0.40b0",
"opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
```

### Prometheus scrape config (`config/prometheus.yml`)

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: api-gateway
    static_configs:
      - targets: ["api-gateway:8000"]
    metrics_path: /metrics

  - job_name: orchestrator
    static_configs:
      - targets: ["orchestrator:8001"]
    metrics_path: /metrics
```

Prometheus reads this file at startup and scrapes each target every 15 seconds. Each scrape is one HTTP `GET /metrics` call.

---

## Walkthrough

### What you get for free

`prometheus_fastapi_instrumentator` automatically tracks every HTTP request with these metrics:

| Metric | Type | Labels |
|--------|------|--------|
| `http_request_duration_seconds` | Histogram | `method`, `handler`, `status` |
| `http_requests_total` | Counter | `method`, `handler`, `status` |
| `http_request_size_bytes` | Histogram | `method`, `handler` |
| `http_response_size_bytes` | Histogram | `method`, `handler` |

No configuration required. Every route (`POST /research`, `GET /research/{id}/events`, `GET /health`) gets measured automatically.

### The pull model

Prometheus is unusual: it **pulls** metrics from services rather than services **pushing** to Prometheus.

```
Push model (e.g. StatsD):
  service → emit metric → metrics server

Pull model (Prometheus):
  service → expose /metrics
  prometheus → scrape /metrics every 15s → store time series
```

Why pull? Services don't need to know Prometheus exists. You can add or reconfigure Prometheus without touching service code. If a service goes down, Prometheus notices (the scrape fails) — you don't need the service to report its own death.

### How `/metrics` looks

```
# HELP http_request_duration_seconds Duration of HTTP requests
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{handler="POST /research",method="POST",status="2xx",le="0.005"} 3
http_request_duration_seconds_bucket{handler="POST /research",method="POST",status="2xx",le="0.01"} 5
...
http_request_duration_seconds_count{handler="POST /research",method="POST",status="2xx"} 12
http_request_duration_seconds_sum{handler="POST /research",method="POST",status="2xx"} 0.843
```

Each histogram line is one bucket (`le` = "less than or equal"). The count and sum let Prometheus compute averages. The buckets let it compute percentiles.

### Why histograms instead of averages

An average latency of 200ms sounds fine. But if p99 is 8 seconds, 1% of users are waiting 8 seconds. An average hides that completely.

A histogram stores how many requests fell into each latency bucket. From that you compute:
- `p50` (median): 50% of requests were faster than this
- `p99`: 99% of requests were faster than this — the "long tail"

In PromQL: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` gives you the p99 latency over the last 5 minutes.

---

## Workflow

```
Startup:
  api-gateway starts → Instrumentator registers middleware
                     → /metrics route mounted on FastAPI app

Every request:
  POST /research → middleware records start time
                → handler runs
                → middleware records end time
                → increments http_request_duration_seconds bucket
                → increments http_requests_total counter

Every 15 seconds:
  prometheus → GET api-gateway:8000/metrics
            → receives Prometheus text format
            → stores each metric as a time series data point

Grafana:
  PromQL query → Prometheus HTTP API → returns time series → Grafana renders panel
```

> [!tip]
> To see raw metrics before Grafana is set up: `curl localhost:8000/metrics` (with the service running locally) or `docker compose exec api-gateway curl localhost:8000/metrics`.

> [!note]
> The gRPC services (planner, search, summarizer, critic, report) do **not** expose a `/metrics` endpoint — they have no HTTP server. Their observability comes from OTel traces (see [[06 OpenTelemetry Tracing]]) and logs (see [[05 Loki and Promtail]]).
