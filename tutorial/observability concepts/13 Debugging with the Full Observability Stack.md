---
tags: [observability, debugging, grafana, prometheus, loki, opentelemetry]
---

# 13 Debugging with the Full Observability Stack

> The real value of observability appears when you use the tools together instead of treating them as separate dashboards.

Related: [[14 Production Observability Thinking]] · [[01 Observability Overview]] · [[Home]]

---

## A Good Debugging Loop

When something feels slow or broken in this repo, a healthy sequence is:

1. Check Grafana dashboards for rate, error, and latency changes
2. Open a trace in Tempo to see which hop was slow
3. Open Loki logs for the task or service involved
4. Use metrics again to confirm whether the issue is isolated or widespread

## Example

Suppose `POST /research` feels slow:

1. Prometheus-backed dashboard shows workflow duration climbing
2. Tempo trace shows the longest span is `GenerateReport`
3. Loki logs show rate limiting or retry behavior in the report service
4. Metrics show the slowdown affects many tasks, not just one

That is a complete debugging story.

## Why This Matters for This Repo

The research workflow crosses many boundaries. Single-tool debugging usually leaves gaps. The combined workflow closes those gaps.
