---
tags: [observability, loki, promtail, project, logql]
file: config/loki.yaml
---

# 09 Loki and Promtail in This Project

> The project's Loki stack turns container logs into something you can actually navigate by service and task.

Related: [[10 OpenTelemetry Fundamentals]] · [[05 Loki and Promtail]] · [[Home]]

---

## The Repo Wiring

The relevant files are:

- [`config/loki.yaml`](/d:/learning-microservice/config/loki.yaml:1)
- [`config/promtail.yaml`](/d:/learning-microservice/config/promtail.yaml:1)
- [`shared/logging.py`](/d:/learning-microservice/shared/logging.py:1)

Together they define:

- where logs are stored
- how logs are discovered
- which fields become labels

## The Most Useful Labels Here

The project promotes:

- `service`
- `level`
- `task_id`

Those labels make cross-service debugging much easier. `task_id` is especially valuable because one research request can span many containers.

## Example Questions Loki Can Answer

- show every log line for task `abc-123`
- show all orchestrator errors
- show all error logs across all services in the last 15 minutes

This is why Loki belongs in the stack even when traces exist. Traces tell you where time went; logs tell you what the code said.
