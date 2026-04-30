---
tags: [redpanda, kafka, docker-compose, infrastructure]
file: docker-compose.yml
---

# 08 Redpanda in docker-compose

> The `docker-compose.yml` entry is where Kafka stops being a concept note and becomes running infrastructure.

Related: [[09 API Gateway Kafka Producer Flow]] · [[03 Redpanda for Local Development]] · [[Home]]

---

## The Service Definition

This repo runs Redpanda from [`docker-compose.yml`](/d:/learning-microservice/docker-compose.yml:50):

```yaml
redpanda:
  image: redpandadata/redpanda:latest
  ports:
    - "9092:9092"
  command: >
    redpanda start
    --overprovisioned
    --smp 1
    --memory 512M
    --reserve-memory 0M
    --node-id 0
    --kafka-addr PLAINTEXT://0.0.0.0:9092
    --advertise-kafka-addr PLAINTEXT://redpanda:9092
```

## The Most Important Flag

`--advertise-kafka-addr PLAINTEXT://redpanda:9092`

This tells Redpanda what broker address to hand back to clients. Inside the Docker network, services reach the broker by service name, so `redpanda:9092` is the correct advertised address.

If this is wrong, clients may connect to the bootstrap address but fail when the broker tells them to reconnect somewhere unreachable.

## Healthcheck

The repo also uses a healthcheck:

```yaml
healthcheck:
  test: ["CMD-SHELL", "rpk cluster health | grep -E 'Healthy:.+true' || exit 1"]
```

This is doing real work for us. It prevents dependent services from starting before the broker is actually ready.

## Why Compose Matters Architecturally

The compose file is not just deployment plumbing. It encodes several design truths:

- Kafka is now a first-class dependency of the gateway and orchestrator
- local development uses service discovery by container name
- broker readiness matters to startup order

Reading the compose file alongside the Python code gives you the complete picture.
