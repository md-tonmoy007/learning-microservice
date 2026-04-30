---
tags: [redpanda, kafka, concepts]
---

# 02 Kafka Core Concepts

> The hardest part of Kafka is the vocabulary. Once the terms click, the rest of the system becomes much easier to reason about.

Related: [[03 Redpanda for Local Development]] · [[Kafka and Redpanda]] · [[Home]]

---

## Topic

A **topic** is a named stream of messages.

Examples from this repo:

- `research.created`
- `research.planned`
- `research.search.completed`
- `research.completed`

Services publish to topics and consume from topics. The topic is the meeting place.

## Producer

A **producer** writes messages to a topic.

In this repo:

- `api-gateway` produces `research.created`
- `orchestrator` produces the progress topics

## Consumer

A **consumer** reads messages from a topic.

In this repo:

- `orchestrator` consumes `research.created`
- the gateway SSE endpoint consumes progress topics

## Offset

An **offset** is the position of a message in a topic log.

Kafka tracks offsets per **consumer group**, not per service process. That means a consumer group can stop, restart, and continue where it left off.

## Consumer Group

A **consumer group** is a logical reader identity.

This matters a lot:

- if two different services need the same event, they use different groups
- if two instances of the same service share work, they use the same group

In this repo, the orchestrator uses a stable group like `orchestrator`. SSE consumers use per-connection group IDs because each browser connection wants its own read position.

## Partition

A **partition** is one ordered shard of a topic.

Ordering is guaranteed within a partition, not across all partitions globally. That is why keys matter.

## Key

A **key** decides which partition a message goes to.

This repo uses `task_id` as the Kafka key. That keeps all events for one research task together and preserves their ordering.

## Mental Model

Think about Kafka like this:

- topics are named logs
- producers append to those logs
- consumers move through those logs using offsets
- consumer groups define who "you" are as a reader

Once you hold that model, the repo's Phase 3 design becomes very readable.
