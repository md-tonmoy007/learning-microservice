---
tags: [observability, prometheus, project, fastapi]
file: config/prometheus.yml
---

# 04 Prometheus in This Project

> In this repo, Prometheus watches the HTTP-facing services by scraping their `/metrics` endpoints every 15 seconds.

Related: [[05 Grafana Fundamentals]] · [[02 Prometheus Metrics]] · [[Home]]

---

## What Gets Scraped

The scrape config lives in [`config/prometheus.yml`](/d:/learning-microservice/config/prometheus.yml:1).

It currently targets:

- `api-gateway:8000`
- `orchestrator:8001`

Both expose `/metrics` through `prometheus_fastapi_instrumentator`.

## Why Only Those Two

The gRPC agent services do not run HTTP apps, so they do not expose `/metrics` the same way. Their visibility comes mainly from:

- traces through OpenTelemetry
- logs through Loki

That split is worth noticing because it reflects the actual shape of the services.

## What Metrics We Get

From the FastAPI instrumentator:

- request counts
- request duration histograms
- request and response size histograms

From custom orchestrator metrics in `services/orchestrator/app/services/research.py`:

- `research_tasks_total`
- `llm_workflow_duration_seconds`

## Why This Is Enough for Phase 4

This gives the project a strong first layer:

- HTTP latency trends
- request volume
- task success and failure counts
- end-to-end workflow duration

That is enough to see whether the system is healthy before drilling into logs or traces.
