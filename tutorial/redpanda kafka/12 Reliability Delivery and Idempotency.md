---
tags: [redpanda, kafka, reliability, delivery, idempotency]
---

# 12 Reliability Delivery and Idempotency

> Once you introduce messaging, you stop asking only "did the service run?" and start asking "what happens if this event arrives twice, late, or after a restart?"

Related: [[13 Debugging Kafka and Redpanda Locally]] · [[10 Orchestrator Kafka Consumer Flow]] · [[Home]]

---

## Delivery Semantics in Practice

The main delivery ideas to know are:

- at-most-once: messages may be lost, but not redelivered
- at-least-once: messages may be redelivered, so consumers must tolerate duplicates
- exactly-once: possible in narrower contexts, but costly and easy to misunderstand

Most real systems live in the at-least-once world.

## Why Idempotency Matters Here

Imagine the orchestrator receives `research.created`, starts work, and then crashes during processing. Depending on commit timing and restart behavior, that message may be seen again.

That means the consumer logic must ask:

- if this task already exists, should I insert again?
- if this event is repeated, how do I avoid corrupting state?

The repo already shows a mild form of this thinking by handling existing task IDs when inserting.

## Practical Idempotency Patterns

Common patterns include:

- using stable IDs from the publisher, like `task_id`
- treating inserts as upserts where appropriate
- checking whether work is already completed before re-running it
- designing event handlers so repeated processing is harmless

## Why This Is a Good Learning Step

You do not need a perfect production-grade reliability story on day one. You do need to start thinking in these terms as soon as you adopt Kafka.

That is the real lesson:

- messaging adds flexibility
- messaging also adds responsibility around duplicate handling and recovery
