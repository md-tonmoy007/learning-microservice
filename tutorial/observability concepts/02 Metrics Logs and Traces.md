---
tags: [observability, metrics, logs, traces]
---

# 02 Metrics Logs and Traces

> Observability has three main signals. Each one is useful alone, but they become much more powerful together.

Related: [[03 Prometheus Fundamentals]] · [[07 Loki and Structured Logging]] · [[10 OpenTelemetry Fundamentals]] · [[Home]]

---

## Metrics

Metrics are numeric summaries over time.

They answer questions like:

- how many requests per second?
- what is p99 latency?
- how many tasks failed in the last hour?

Metrics are great for dashboards, trends, alerts, and capacity thinking.

## Logs

Logs are timestamped records of what happened.

They answer questions like:

- what exact error occurred?
- what input triggered it?
- what sequence of messages did a specific task produce?

Logs are great for narrative detail and debugging context.

## Traces

Traces show one request or workflow moving across services.

They answer questions like:

- which hop was slow?
- how are these service calls related?
- which downstream dependency dominated total latency?

Traces are great for end-to-end timing and dependency understanding.

## Why One Signal Is Not Enough

Metrics can show that latency spiked, but not why. Logs can show an error, but not how much system-wide impact it had. Traces can show a slow span tree, but not long-term trends.

This repo uses all three because the architecture has all three kinds of questions.
