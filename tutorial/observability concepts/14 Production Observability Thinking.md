---
tags: [observability, production, operations]
---

# 14 Production Observability Thinking

> Local observability teaches the concepts. Production observability adds retention, scale, alerting, and operational discipline.

Related: [[00 Observability Series Index]] · [[01 Why Observability Matters]] · [[Home]]

---

## What Gets More Important in Production

- alerting thresholds
- metric cardinality control
- log retention and storage cost
- trace sampling strategy
- dashboard quality
- on-call usability

## What Stays the Same

The core mental model stays the same:

- Prometheus answers quantitative questions
- Loki answers narrative questions from logs
- OpenTelemetry and Tempo answer end-to-end timing questions
- Grafana ties the workflow together

## Why This Repo Is a Good Training Ground

The stack here is small enough to understand but realistic enough to teach the right instincts. If you can explain how Prometheus, Grafana, Loki, Promtail, Tempo, and OpenTelemetry fit together in this repo, you already have the right foundation for a much larger system.
