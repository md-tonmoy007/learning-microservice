---
tags: [redpanda, kafka, architecture, event-driven]
---

# 01 Why Event Streaming Matters

> Kafka is not just a queue. It is the backbone that lets services communicate without tight runtime coupling.

Related: [[02 Kafka Core Concepts]] · [[01 Event-Driven Architecture]] · [[Home]]

---

## The Before and After

In the early version of this project, the `api-gateway` called the `orchestrator` directly over HTTP. That works, but it creates a dependency chain:

```text
user -> api-gateway -> orchestrator -> workflow
```

The gateway has to know where the orchestrator lives. It has to wait for a response. If the orchestrator is down, the request path breaks immediately.

Phase 3 changes this:

```text
user -> api-gateway -> Kafka topic -> orchestrator
```

Now the gateway publishes an event and returns a `task_id` immediately. The orchestrator picks the event up independently.

## Why This Matters

- It decouples the `api-gateway` from the `orchestrator`
- It makes async workflows feel natural instead of awkward
- It gives us a stream of progress events instead of one final response
- It opens the door to replay, retries, auditing, and independent subscribers

## In This Repo

The Phase 3 flow looks like this:

1. `POST /research` lands at the gateway
2. The gateway generates a `task_id`
3. The gateway publishes `research.created`
4. The orchestrator consumes that event and runs LangGraph
5. The orchestrator publishes progress events as each node completes
6. The gateway streams those events to the browser with SSE

This is why Kafka appears in the architecture at the exact moment the project moves from "call another service" to "coordinate a distributed workflow".

## What to Notice

Kafka is solving a system-design problem here, not just a transport problem. It changes the shape of the architecture:

- request/response becomes publish/consume
- blocking becomes asynchronous
- one final status becomes an event timeline

That shift is the reason to learn Kafka in this repo.
