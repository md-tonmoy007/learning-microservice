---
tags: [observability, series, index, prometheus, grafana, loki, opentelemetry]
---

# 00 Observability Series Index

> A step-by-step observability series for understanding metrics, logs, traces, and how this repo wires them together.

Related: [[01 Observability Overview]] · [[Prometheus]] · [[Grafana]] · [[OpenTelemetry]] · [[Home]]

---

## Read in Order

1. [[01 Why Observability Matters]]
2. [[02 Metrics Logs and Traces]]
3. [[03 Prometheus Fundamentals]]
4. [[04 Prometheus in This Project]]
5. [[05 Grafana Fundamentals]]
6. [[06 Grafana in This Project]]
7. [[07 Loki and Structured Logging]]
8. [[08 Promtail Log Shipping]]
9. [[09 Loki and Promtail in This Project]]
10. [[10 OpenTelemetry Fundamentals]]
11. [[11 Tempo and the OTel Collector]]
12. [[12 OpenTelemetry in This Project]]
13. [[13 Debugging with the Full Observability Stack]]
14. [[14 Production Observability Thinking]]

## How This Series Fits the Repo

Phase 4 turns the project from "it works" into "we can see how it works."

- Prometheus scrapes `/metrics` from the HTTP services
- Grafana provides dashboards and Explore views
- Promtail reads container logs and ships them to Loki
- OpenTelemetry creates spans for HTTP and gRPC calls
- The OTel Collector forwards traces to Tempo

If the tool names feel familiar but fuzzy, read from the top. If you already know the three pillars, you can jump to [[04 Prometheus in This Project]], [[06 Grafana in This Project]], [[09 Loki and Promtail in This Project]], and [[12 OpenTelemetry in This Project]].
