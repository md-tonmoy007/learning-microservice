---
tags: [redpanda, kafka, series, index]
---

# 00 Series Index

> A step-by-step note series for learning Kafka and Redpanda in the context of this repo's event-driven architecture.

Related: [[Kafka and Redpanda]] · [[01 Event-Driven Architecture]] · [[02 Redpanda and Kafka Events]] · [[Home]]

---

## Read in Order

1. [[01 Why Event Streaming Matters]]
2. [[02 Kafka Core Concepts]]
3. [[03 Redpanda for Local Development]]
4. [[04 Producers Events and Keys]]
5. [[05 Consumers Consumer Groups and Offsets]]
6. [[06 Topics Partitions and Ordering]]
7. [[07 Event Design and Shared Contracts]]
8. [[08 Redpanda in docker-compose]]
9. [[09 API Gateway Kafka Producer Flow]]
10. [[10 Orchestrator Kafka Consumer Flow]]
11. [[11 SSE Redis and User Feedback]]
12. [[12 Reliability Delivery and Idempotency]]
13. [[13 Debugging Kafka and Redpanda Locally]]
14. [[14 Production Kafka Beyond Local Dev]]

## How This Series Fits the Repo

This repo introduces Kafka in Phase 3.

- The `api-gateway` publishes `research.created`
- The `orchestrator` consumes that event and starts LangGraph
- The `orchestrator` publishes progress events like `research.planned`
- The `api-gateway` consumes progress topics and forwards them through SSE
- Redis stores fast status snapshots for polling endpoints

If you already know basic messaging, start at [[07 Event Design and Shared Contracts]]. If Kafka is still new, read from the top in order.
