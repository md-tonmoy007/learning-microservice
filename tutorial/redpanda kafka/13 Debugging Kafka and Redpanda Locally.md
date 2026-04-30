---
tags: [redpanda, kafka, debugging, local-dev]
file: docker-compose.yml
---

# 13 Debugging Kafka and Redpanda Locally

> Most Kafka confusion in local development comes from a small set of issues: wrong broker address, unhealthy startup order, wrong consumer group expectations, or offset surprises.

Related: [[14 Production Kafka Beyond Local Dev]] · [[08 Redpanda in docker-compose]] · [[Home]]

---

## If Events Are Not Flowing

Check the path in order:

1. Is the `redpanda` container healthy?
2. Are services using the right `KAFKA_BOOTSTRAP_SERVERS` value?
3. Is `--advertise-kafka-addr` correct for the Docker network?
4. Is the producer publishing to the exact topic constant you expect?
5. Is the consumer subscribed to that topic with the group ID you think it has?

## Classic Offset Confusion

A very common mistake is assuming a consumer will always read all past events. That is only true for a new group with the right offset reset behavior.

If a stable group has already committed offsets, restarting the service will resume from there, not replay from the beginning.

## Classic Group Confusion

If two independent readers accidentally share a group, they will divide work instead of both seeing every message.

When debugging, always ask:

- are these readers supposed to share work?
- or are they supposed to independently observe the same topic?

That one question clears up a lot.

## Useful Repo Files to Read Together

- [`docker-compose.yml`](/d:/learning-microservice/docker-compose.yml:1)
- [`shared/kafka_events.py`](/d:/learning-microservice/shared/kafka_events.py:1)
- [`services/api-gateway/app/core/kafka.py`](/d:/learning-microservice/services/api-gateway/app/core/kafka.py:1)
- [`services/orchestrator/app/core/kafka.py`](/d:/learning-microservice/services/orchestrator/app/core/kafka.py:1)
- [`services/api-gateway/app/api/research.py`](/d:/learning-microservice/services/api-gateway/app/api/research.py:1)

Reading those together usually tells the whole story.
