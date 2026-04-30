---
tags: [redpanda, kafka, production, architecture]
---

# 14 Production Kafka Beyond Local Dev

> Redpanda in local Docker teaches the event model. Production Kafka adds scaling, replication, and stronger operational discipline.

Related: [[00 Series Index]] · [[01 Event-Driven Architecture]] · [[Home]]

---

## What Changes in Production

The application concepts stay mostly the same:

- producers publish events
- consumers read by group
- keys affect partitioning and ordering
- offsets define reading progress

What changes is the operational environment:

- multiple brokers instead of one local node
- replication instead of single-copy local storage
- topic configuration as an intentional design decision
- monitoring and lag analysis become essential

## Design Questions That Get More Important

In production, you usually make more explicit choices around:

- partition count
- retention policy
- replication factor
- dead-letter handling
- consumer lag monitoring
- schema evolution discipline

The repo points toward that future, even though it keeps the local setup intentionally simple.

## The Nice Part

Because the code already uses Kafka-compatible clients and clear event contracts, moving from local Redpanda to a production Kafka cluster is mostly an infrastructure move, not an application rewrite.

That is exactly why this repo is structured the way it is. We get the learning value of a simple environment while keeping the architecture aligned with real distributed systems.
