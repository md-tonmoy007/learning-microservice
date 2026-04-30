---
tags: [redpanda, kafka, partitions, ordering]
---

# 06 Topics Partitions and Ordering

> Kafka gives you durable ordering, but the scope of that ordering is smaller than many people assume.

Related: [[04 Producers Events and Keys]] · [[05 Consumers Consumer Groups and Offsets]] · [[Home]]

---

## Ordering Is Per Partition

Kafka guarantees message order within a single partition.

It does **not** guarantee one global order across every partition of a topic.

That means the real question is not "does Kafka preserve order?" but "which messages are routed to the same partition?"

## Why the Key Matters

This repo uses:

```python
key=event["task_id"].encode()
```

That keeps all events for one task on the same partition. As a result, one task's event stream stays readable:

```text
task-123 -> created -> planned -> searched -> summarized -> completed
```

Another task can progress independently without interfering with that ordering.

## Topic Naming in This Repo

The repo uses dot-separated names:

- `research.created`
- `research.planned`
- `research.search.completed`
- `research.failed`

That naming scheme carries meaning:

- `research` is the domain namespace
- later words refine the stage or outcome

Good topic names help humans navigate the system just as much as they help code.

## Partition Strategy for a Learning Repo

For this project, one partition per topic is enough to teach the model. That keeps behavior easier to inspect.

In a production system, you increase partitions for throughput and parallelism, but that comes with tradeoffs:

- more ordering boundaries
- more consumer balancing behavior
- more operational decisions around scale

This is why the repo starts simple. The concept matters more than the raw partition count here.
