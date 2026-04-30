---
tags: [concept, prometheus, metrics, observability]
---

# Prometheus

> Prometheus is a time-series database that collects metrics by scraping HTTP endpoints every few seconds, letting you query trends and percentiles with PromQL.

Used in: [[02 Prometheus Metrics]] · [[03 Custom Metrics Orchestrator]] · [[04 Grafana Dashboards]]

---

## The Core Idea

Prometheus is a **pull-based** metrics system. Services expose a `/metrics` HTTP endpoint. Prometheus periodically fetches it and stores each metric as a time series — a sequence of (timestamp, value) pairs.

```
service  →  GET /metrics (every 15s by Prometheus)
         ←  returns text: metric_name{labels} value

Prometheus stores:
  http_requests_total{method="POST",status="200"} @ t=0   →  12
  http_requests_total{method="POST",status="200"} @ t=15  →  15
  http_requests_total{method="POST",status="200"} @ t=30  →  19
```

You query these time series with PromQL.

---

## Metric Types

**Counter** — monotonically increasing. Only goes up. Counts events.
```python
from prometheus_client import Counter
requests_total = Counter("requests_total", "Total requests", ["method"])
requests_total.labels(method="POST").inc()
```
Use `rate()` in PromQL to get per-second rate; `increase()` for total in a window.

**Histogram** — records observations in buckets. Used for durations and sizes.
```python
from prometheus_client import Histogram
duration = Histogram("request_duration_seconds", "Request latency")
with duration.time():
    do_work()
```
Use `histogram_quantile()` to get p50/p99. Produces `_bucket`, `_count`, `_sum` series.

**Gauge** — goes up and down. Snapshots current state.
```python
from prometheus_client import Gauge
active = Gauge("active_connections", "Current active connections")
active.inc()   # connection opened
active.dec()   # connection closed
```

**Summary** — like a histogram but computes quantiles client-side. Avoid for new code — histograms are more flexible.

---

## The Pull Model

```
Push (StatsD, CloudWatch):
  service → metric → metrics server
  Problem: if service is down, it stops sending — hard to detect

Pull (Prometheus):
  prometheus → GET /metrics → service
  Problem: if service is down, scrape fails → Prometheus alerts on "up == 0"
```

Pull means:
- Services don't know Prometheus exists — no dependency
- Prometheus tracks which services are up via scrape success/failure
- You can change scrape frequency without touching service code

---

## Scrape Config

`config/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s   # scrape every 15 seconds

scrape_configs:
  - job_name: my-service
    static_configs:
      - targets: ["my-service:8000"]
    metrics_path: /metrics   # default, can omit
```

`job_name` becomes a label on every metric from that target: `{job="my-service"}`. Use it in PromQL to scope queries to one service.

---

## PromQL Essentials

```promql
# Current value
http_requests_total

# Filter by label
http_requests_total{job="api-gateway", status="2xx"}

# Rate over 1 minute (for counters)
rate(http_requests_total[1m])

# Total increase over 1 hour
increase(http_requests_total[1h])

# p99 latency from a histogram
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)

# Sum across all methods, keep job label
sum by (job) (rate(http_requests_total[1m]))

# Error ratio
rate(http_requests_total{status=~"5.."}[1m])
/ rate(http_requests_total[1m])
```

> [!tip]
> Always use `rate()` with counters in Grafana panels, never raw counter values. A raw counter always goes up — the graph is useless. `rate()` shows how fast it's growing, which is what you actually care about.
