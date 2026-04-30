---
tags: [observability, loki, logging, structured-logs]
file: shared/logging.py
---

# 07 Loki and Structured Logging

> Loki works best when logs are structured before they ever leave the service.

Related: [[08 Promtail Log Shipping]] · [[Loki and Promtail]] · [[Home]]

---

## Why Structured Logs Matter

Free-form text logs are easy to write but hard to query. Structured logs turn one log line into a machine-readable event.

This repo already emits JSON logs from [`shared/logging.py`](/d:/learning-microservice/shared/logging.py:1).

Each line includes fields like:

- `timestamp`
- `level`
- `service`
- `message`
- optional `task_id`
- optional `event`

## Why Loki Likes This

Promtail can parse JSON fields and promote some of them into labels. That makes filtering much more useful than raw text search alone.

For example:

- all logs for one service
- all logs for one `task_id`
- all `ERROR` logs across services

## What Loki Is Optimized For

Loki indexes labels, not full log text. That is the key design difference from search systems that index everything.

This keeps storage cheaper and the design simpler, but it also means label choice matters.
