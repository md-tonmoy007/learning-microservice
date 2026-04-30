---
tags: [observability, promtail, loki, log-shipping]
file: config/promtail.yaml
---

# 08 Promtail Log Shipping

> Promtail is the bridge between container stdout and Loki.

Related: [[09 Loki and Promtail in This Project]] · [[05 Loki and Promtail]] · [[Home]]

---

## What Promtail Does

Promtail discovers log sources, reads lines, attaches labels, and pushes batches to Loki.

In this repo it uses Docker service discovery through [`config/promtail.yaml`](/d:/learning-microservice/config/promtail.yaml:1).

## The Flow

```text
containers write logs to stdout
promtail discovers containers through docker.sock
promtail parses JSON log lines
promtail attaches labels like service, level, and task_id
promtail pushes the logs to loki
```

## Why Docker Metadata Helps

Docker Compose already knows service names, so Promtail can reuse that metadata. This means the repo does not need custom per-service shipping logic.

## Why `positions.yaml` Matters

Promtail tracks how far it has read from each log stream. That prevents replaying the entire log history every time Promtail restarts.
