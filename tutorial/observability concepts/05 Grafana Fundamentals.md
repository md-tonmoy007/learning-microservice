---
tags: [observability, grafana, dashboards]
---

# 05 Grafana Fundamentals

> Grafana is not the storage engine here. It is the observability workspace where the other tools become usable together.

Related: [[06 Grafana in This Project]] · [[Grafana]] · [[Home]]

---

## What Grafana Actually Does

Grafana connects to observability backends as datasources and gives you:

- dashboards
- ad-hoc exploration
- cross-linking between metrics, logs, and traces

It does not replace Prometheus, Loki, or Tempo. It sits on top of them.

## The Three Datasource Roles

- Prometheus: numeric time series and PromQL
- Loki: log streams and LogQL
- Tempo: traces and span views

Grafana is the one place where you can pivot between all three.

## Why This Matters

A useful observability workflow often looks like this:

1. See a spike on a Grafana dashboard
2. Open a trace around that time
3. Jump from the trace to logs

That is much faster than querying three separate systems manually.
