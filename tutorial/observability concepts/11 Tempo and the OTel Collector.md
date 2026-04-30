---
tags: [observability, tempo, otel-collector, tracing]
file: config/otel-collector.yaml
---

# 11 Tempo and the OTel Collector

> The application does not send traces directly to Grafana. It sends them to the OTel Collector, which forwards them to Tempo.

Related: [[12 OpenTelemetry in This Project]] · [[06 OpenTelemetry Tracing]] · [[Home]]

---

## Why There Is a Collector in the Middle

The OpenTelemetry Collector is a routing and processing layer. Services emit OTLP spans to one place, and the collector decides where they go next.

In this repo:

- services send spans to `otel-collector:4317`
- the collector exports them to Tempo
- the collector also logs debug output

## Why Tempo Exists

Tempo is the trace storage backend. It stores traces so Grafana can search and render them.

That means the roles are separate:

- OpenTelemetry SDK: creates spans
- OTel Collector: receives and forwards spans
- Tempo: stores traces
- Grafana: visualizes traces

## Repo Files

- [`config/otel-collector.yaml`](/d:/learning-microservice/config/otel-collector.yaml:1)
- [`config/tempo.yaml`](/d:/learning-microservice/config/tempo.yaml:1)

This split is architecturally clean and mirrors how larger systems are usually built.
