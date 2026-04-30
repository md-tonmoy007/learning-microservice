---
tags: [observability, prometheus, metrics]
---

# 03 Prometheus Fundamentals

> Prometheus is the metrics engine in this repo. Its job is simple: scrape metrics endpoints, store time series, and answer PromQL queries.

Related: [[04 Prometheus in This Project]] · [[Prometheus]] · [[Home]]

---

## The Core Model

Prometheus uses a pull model:

```text
service exposes /metrics
prometheus scrapes /metrics every N seconds
prometheus stores the results as time series
```

A time series is just a metric name plus labels plus timestamped values.

## Useful Metric Types

- `Counter`: only goes up, good for totals
- `Histogram`: records values into buckets, good for latency and sizes
- `Gauge`: goes up and down, good for current state

This repo mostly leans on counters and histograms.

## Why Histograms Matter

Latency is not well described by an average alone. A system can have a friendly average and still have terrible long-tail latency.

Histograms let you ask:

- p50 latency
- p95 latency
- p99 latency

That is why Prometheus fits service observability so well.

## PromQL in One Sentence

PromQL is the query language you use to ask questions about metrics over time. It powers Grafana metric dashboards in this repo.
