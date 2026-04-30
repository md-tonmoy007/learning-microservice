---
tags: [observability, concepts, architecture]
---

# 01 Why Observability Matters

> Observability is how a distributed system explains itself from the outside.

Related: [[02 Metrics Logs and Traces]] · [[01 Observability Overview]] · [[Home]]

---

## The Problem It Solves

By Phase 3, this repo already has:

- an API gateway
- an orchestrator
- five gRPC agent services
- Kafka events
- Redis status caching

That is enough moving parts for "it failed" to stop being a useful answer.

Questions start to sound like this:

- Why did one research task take 8 seconds and another take 45?
- Was the slowdown in HTTP, LangGraph, gRPC, Kafka, or the LLM call?
- Which service logged the actual error?
- Is the system getting slower over time or was this a one-off?

Observability exists to answer those questions quickly.

## Why It Matters More in Microservices

In a single process, debugging can often be done by stepping through code and reading one log stream. In this repo, one user request can touch:

- `api-gateway`
- `orchestrator`
- `planner-agent`
- `search-agent`
- `summarizer-agent`
- `critic-agent`
- `report-service`

Without observability, the system's behavior is scattered across containers.

## What Good Observability Gives You

It lets you answer three different kinds of questions:

- How much, how often, how fast?
- What happened and what did the system say?
- Where exactly did time go across services?

Those map directly to metrics, logs, and traces.
