---
tags: [phase-4, grafana, prometheus, promql, dashboards]
file: config/grafana/provisioning/datasources/datasources.yaml
---

# 04 Grafana Dashboards

> Grafana is the single UI for all three observability signals. One datasource points at Prometheus for metrics, one at Loki for logs, one at Tempo for traces — all provisioned automatically on startup.

Related: [[Grafana]] · [[Prometheus]] · [[02 Prometheus Metrics]] · [[05 Loki and Promtail]] · [[Home]]

---

## The Code

### Datasource provisioning (`config/grafana/provisioning/datasources/datasources.yaml`)

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    editable: true
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
      lokiSearch:
        datasourceUid: loki
```

### Grafana in docker-compose.yml

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: admin
    GF_INSTALL_PLUGINS: grafana-tempo-datasource
  volumes:
    - grafana_data:/var/lib/grafana
    - ./config/grafana/provisioning:/etc/grafana/provisioning
  depends_on:
    - prometheus
    - loki
    - tempo
```

---

## Walkthrough

### Provisioning vs manual setup

Grafana normally requires you to click through the UI to add datasources. **Provisioning** reads YAML files at startup and configures them automatically. When you `docker compose down -v` and bring everything back up, datasources are still there — no clicking required.

The volume mount `./config/grafana/provisioning:/etc/grafana/provisioning` makes Grafana read your provisioning files. The `datasources/` subdirectory is a Grafana convention — it scans every `.yaml` file in that directory.

### Accessing Grafana

```
URL:      http://localhost:3000
Username: admin
Password: admin   (set via GF_SECURITY_ADMIN_PASSWORD)
```

Datasources appear under **Connections → Data sources** — all three are already connected.

### The six dashboards to build

Grafana dashboards are built in the browser UI using PromQL panels. These are the six dashboards from `docs/phase-4.md` and the PromQL to power them:

**1. API Gateway — request traffic**
```promql
# Request rate (requests/second)
rate(http_requests_total{job="api-gateway"}[1m])

# p99 latency
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket{job="api-gateway"}[5m])
)

# Error rate (5xx fraction)
rate(http_requests_total{job="api-gateway",status=~"5.."}[1m])
/ rate(http_requests_total{job="api-gateway"}[1m])
```

**2. Research workflow duration**
```promql
# p50 and p99 end-to-end workflow time
histogram_quantile(0.50, rate(llm_workflow_duration_seconds_bucket[10m]))
histogram_quantile(0.99, rate(llm_workflow_duration_seconds_bucket[10m]))

# Tasks per minute
rate(research_tasks_total_total{status="completed"}[1m]) * 60
```

**3. Task outcomes**
```promql
# Success vs failure over time
increase(research_tasks_total_total{status="completed"}[1h])
increase(research_tasks_total_total{status="failed"}[1h])

# Failure rate
rate(research_tasks_total_total{status="failed"}[5m])
/ rate(research_tasks_total_total{status="started"}[5m])
```

**4. Orchestrator HTTP traffic** (same pattern as API Gateway, `job="orchestrator"`)

**5. In-flight tasks**
```promql
# Tasks currently running (started but not yet completed or failed)
increase(research_tasks_total_total{status="started"}[1h])
- increase(research_tasks_total_total{status="completed"}[1h])
- increase(research_tasks_total_total{status="failed"}[1h])
```

**6. System health** — combine error rates from both services in one panel

### PromQL crash course

| Expression | Meaning |
|-----------|---------|
| `metric_name` | Current value of the metric |
| `metric_name[5m]` | Range vector: values over the last 5 minutes |
| `rate(counter[5m])` | Per-second rate of increase, averaged over 5m |
| `increase(counter[1h])` | Total increase over 1 hour |
| `histogram_quantile(0.99, rate(hist_bucket[5m]))` | p99 value from a histogram |
| `sum by (label) (metric)` | Aggregate across series, keep one label |
| `metric{label="value"}` | Filter to a specific label value |
| `metric{label=~"pattern"}` | Filter using a regex |

### Trace-to-logs correlation

The datasource provisioning wires Tempo and Loki together:

```yaml
jsonData:
  tracesToLogsV2:
    datasourceUid: loki
  lokiSearch:
    datasourceUid: loki
```

When you view a trace in the Tempo panel, Grafana adds a "Logs for this span" button that jumps to Loki filtered by the trace ID. This connects the three pillars directly in the UI.

---

## Workflow

```
docker compose up → Grafana reads provisioning/datasources/datasources.yaml
                 → Creates Prometheus datasource at http://prometheus:9090
                 → Creates Loki datasource at http://loki:3100
                 → Creates Tempo datasource at http://tempo:3200

Browser → localhost:3000 → Grafana login (admin/admin)

Dashboards → New → Add panel → Select "Prometheus" datasource
  → Type PromQL: rate(http_requests_total{job="api-gateway"}[1m])
  → Choose visualization: Time series
  → Save dashboard

Explore → Select "Loki" datasource
  → LogQL: {service="orchestrator"} | json | task_id="abc-123"

Explore → Select "Tempo" datasource
  → Search by trace ID from a log line
```

> [!tip]
> Start with the **Explore** tab (compass icon in the left nav) before building dashboards. You can run ad-hoc PromQL and LogQL queries there without committing to a panel layout. Once you know which query answers a useful question, promote it to a dashboard.

> [!note]
> Dashboard JSON can be exported and saved in `config/grafana/provisioning/dashboards/` to make dashboards persistent across restarts. For now, build them manually in the UI to learn the tool — persistence can come later.
