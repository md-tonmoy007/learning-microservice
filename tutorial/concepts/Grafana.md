---
tags: [concept, grafana, dashboards, observability, promql, logql]
---

# Grafana

> Grafana is a dashboard and visualization platform that unifies metrics (Prometheus), logs (Loki), and traces (Tempo) into a single browser UI with linked navigation between all three.

Used in: [[04 Grafana Dashboards]] · [[05 Loki and Promtail]] · [[06 OpenTelemetry Tracing]]

---

## The Core Idea

Without Grafana, you query each observability system separately: `curl localhost:9090` for Prometheus, `curl localhost:3100` for Loki, another tool for traces. Grafana puts them all in one place and lets you navigate between them.

```
Grafana datasources:
  Prometheus → PromQL dashboards (metrics)
  Loki       → LogQL log explorer (logs)
  Tempo      → trace viewer (traces)

Grafana links:
  metric spike → click → trace that caused it
  trace span   → click → logs for that span
  log line     → click → trace for that request
```

---

## Datasources

A **datasource** is a connection to an external system. Grafana queries it on behalf of the user.

In this project, datasources are **provisioned** (auto-configured from YAML at startup):

```yaml
# config/grafana/provisioning/datasources/datasources.yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true

  - name: Loki
    type: loki
    url: http://loki:3100

  - name: Tempo
    type: tempo
    url: http://tempo:3200
```

Without provisioning you'd click through the UI manually after every `docker compose down -v`.

---

## The UI Structure

| Area | Where | What |
|------|-------|------|
| **Dashboards** | left nav → Dashboards | Saved collections of panels |
| **Explore** | compass icon | Ad-hoc queries against any datasource |
| **Alerting** | bell icon | Alert rules and notification channels |
| **Connections** | plug icon | Manage datasources and plugins |

**Start with Explore** when learning — run queries without committing to a layout. When a query proves useful, save it as a dashboard panel.

---

## Panels and Visualizations

A dashboard is a grid of **panels**. Each panel has:
- A **datasource** (Prometheus, Loki, or Tempo)
- A **query** (PromQL, LogQL, or trace search)
- A **visualization** (time series graph, stat, gauge, table, logs, trace viewer)

Common visualizations:
- **Time series** — metric over time, the default for rates and latencies
- **Stat** — single current value with color threshold (green/yellow/red)
- **Bar gauge** — comparison across label values
- **Logs** — log lines from Loki in chronological order
- **Traces** — span tree from Tempo

---

## PromQL vs LogQL

Both are query languages with similar syntax but different purposes.

**PromQL** (Prometheus Query Language):
```promql
rate(http_requests_total{job="api-gateway"}[1m])
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```
Returns numeric time series. Used for metric panels.

**LogQL** (Loki Query Language):
```logql
{service="orchestrator"}                        # stream selector
{service="orchestrator"} |= "Workflow failed"   # filter by content
{service="orchestrator"} | json | level="ERROR" # parse JSON and filter field
sum by (service) (rate({service=~".+"}[1m]))    # metric from logs
```
Returns log lines or derived metrics. Used for log panels and the Explore tab.

---

## Trace-to-Logs Navigation

When Grafana's Tempo datasource is configured with `tracesToLogsV2.datasourceUid: loki`, each span in the trace viewer shows a **"Logs for this span"** button. Clicking it opens Explore with a LogQL query pre-filtered by trace ID.

This requires log lines to include the trace ID. The OTel instrumentors don't automatically add trace IDs to Python's `logging` output — you must add that manually to the shared JSON formatter if you want click-through correlation to work.

---

## Alerting

Grafana can evaluate PromQL queries on a schedule and fire alerts when thresholds are crossed. Example: alert when error rate exceeds 5%:

```promql
rate(http_requests_total{status=~"5.."}[5m])
/ rate(http_requests_total[5m])
> 0.05
```

Alert destinations include email, Slack, PagerDuty, and webhooks. Not configured in Phase 4 — add it when the system goes to production.

> [!tip]
> Grafana's **Explore** tab is the fastest way to debug a live incident. Select Loki, type `{task_id="abc-123"}`, and you see everything that happened to that task across all services in seconds — no SSH, no log files.
