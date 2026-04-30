---
tags: [observability, grafana, project, provisioning]
file: config/grafana/provisioning/datasources/datasources.yaml
---

# 06 Grafana in This Project

> In this repo, Grafana is pre-wired at startup so the observability stack is immediately usable after `docker compose up`.

Related: [[07 Loki and Structured Logging]] · [[04 Grafana Dashboards]] · [[Home]]

---

## Datasource Provisioning

Grafana datasource provisioning lives in [`config/grafana/provisioning/datasources/datasources.yaml`](/d:/learning-microservice/config/grafana/provisioning/datasources/datasources.yaml:1).

That file connects Grafana to:

- Prometheus
- Loki
- Tempo

This is better than manual setup because the environment is reproducible.

## Why Provisioning Helps in a Learning Repo

Without provisioning, every reset of volumes means re-creating the UI configuration by hand. With provisioning:

- startup is consistent
- screenshots and notes stay aligned
- the repo itself documents the observability topology

## What Grafana Lets You Do Here

- inspect Prometheus metrics with PromQL
- search logs in Loki with LogQL
- inspect traces in Tempo
- move from one signal to another while debugging one task

That last point is the big one. Grafana is where the stack becomes a workflow instead of a pile of tools.
