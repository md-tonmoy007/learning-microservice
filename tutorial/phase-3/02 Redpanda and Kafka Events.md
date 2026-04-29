---
tags: [phase-3, kafka, redpanda, events, docker]
file: shared/kafka_events.py
---

# 02 Redpanda and Kafka Events

> All Kafka topic names and the shared event shape live in `shared/kafka_events.py`. Redpanda runs as a single Docker container that is wire-compatible with Kafka.

Related: [[Kafka and Redpanda]] · [[01 Event-Driven Architecture]] · [[Home]]

---

## The Code

**Shared event definitions** (`shared/kafka_events.py`):
```python
from datetime import datetime, timezone

RESEARCH_CREATED    = "research.created"
RESEARCH_PLANNED    = "research.planned"
RESEARCH_SEARCHED   = "research.search.completed"
RESEARCH_SUMMARIZED = "research.summary.completed"
RESEARCH_CRITIQUED  = "research.critique.completed"
RESEARCH_COMPLETED  = "research.completed"
RESEARCH_FAILED     = "research.failed"
AGENT_LOGS          = "agent.logs"

ALL_PROGRESS_TOPICS = [
    RESEARCH_PLANNED,
    RESEARCH_SEARCHED,
    RESEARCH_SUMMARIZED,
    RESEARCH_CRITIQUED,
    RESEARCH_COMPLETED,
    RESEARCH_FAILED,
]

def make_event(task_id: str, event: str, service: str, payload: dict | None = None) -> dict:
    return {
        "task_id": task_id,
        "event": event,
        "service": service,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
```

**Redpanda in docker-compose.yml**:
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
  healthcheck:
    test: ["CMD-SHELL", "rpk cluster health | grep -E 'Healthy:.+true' || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 10
    start_period: 20s
```

---

## Walkthrough

### Why a shared `kafka_events.py`

Without a shared file, each service would hardcode topic name strings. A typo in one service (`"research.create"` vs `"research.created"`) would silently break the workflow — the publisher and consumer would never connect, and no error would appear.

By importing from `shared.kafka_events`, a typo becomes an `ImportError` at startup. The constant is the single source of truth.

The `shared/` package is a workspace member in `pyproject.toml` and is copied into every Docker image. Any service can `from shared.kafka_events import RESEARCH_CREATED`.

### The standard event shape

Every Kafka message in this project follows the same JSON schema:

```json
{
  "task_id":   "abc-123",
  "event":     "research.planned",
  "service":   "orchestrator",
  "timestamp": "2026-04-29T10:30:00.123456+00:00",
  "payload":   { "status": "planned" }
}
```

| Field | Purpose |
|-------|---------|
| `task_id` | Which research run this belongs to — used for filtering in SSE |
| `event` | The topic name string — redundant but useful for logging |
| `service` | Which service published this — useful for debugging |
| `timestamp` | When it was published — use UTC always |
| `payload` | Event-specific data — varies by event type |

`make_event()` handles the timestamp so callers don't have to remember `datetime.now(timezone.utc)`.

### Topic naming convention

Topics use dot-separated namespaces: `research.created`, `research.planned`, `research.search.completed`.

The leading namespace (`research.`) groups all events from this workflow. When Phase 4 adds metrics events, they'll use `metrics.` prefix. This makes Kafka topic lists readable at a glance.

### ALL_PROGRESS_TOPICS — the SSE subscription list

The SSE endpoint in the api-gateway subscribes to all topics that represent workflow progress. Grouping them in `ALL_PROGRESS_TOPICS` means the SSE consumer subscription list stays in sync with the event types automatically — add a new event type, add it to `ALL_PROGRESS_TOPICS`, and the SSE endpoint picks it up.

`RESEARCH_CREATED` is intentionally excluded from this list. The api-gateway publishes it but doesn't need to consume it.

### Redpanda flags explained

```
--overprovisioned       use all available CPU (fine for dev, do not use in prod)
--smp 1                 single CPU core (dev only)
--memory 512M           limit RAM to 512MB
--reserve-memory 0M     don't reserve RAM headroom (single-node dev mode)
--node-id 0             this node's ID in the cluster (we have only one node)
--kafka-addr PLAINTEXT://0.0.0.0:9092    listen on all interfaces
--advertise-kafka-addr PLAINTEXT://redpanda:9092   tell clients to connect to "redpanda"
```

The `--advertise-kafka-addr` is the most important flag. When a client connects to Redpanda and asks "where are the brokers?", Redpanda responds with this address. Inside Docker's network, services reach each other by service name. Setting it to `redpanda:9092` means the bootstrap response tells clients to connect to `redpanda:9092` — which resolves correctly inside Docker.

### Healthcheck — why `rpk cluster health`

`rpk` is Redpanda's built-in CLI. `rpk cluster health` returns a report that includes `Healthy: true` when the cluster is ready to accept connections. The healthcheck grep for that string:

```bash
rpk cluster health | grep -E 'Healthy:.+true'
```

If the cluster isn't ready yet, this exits non-zero and Docker Compose waits before starting dependent services. Both `api-gateway` and `orchestrator` have `depends_on: redpanda: condition: service_healthy` so they don't start until Redpanda is ready to accept connections.

---

## Workflow

```
docker compose up
  ↓
Redpanda starts → passes healthcheck
  ↓
api-gateway starts → calls start_producer("redpanda:9092")
orchestrator starts → calls start_producer("redpanda:9092")
                   → starts run_research_consumer("redpanda:9092", run_workflow)

User: POST /research {"query": "..."}
  ↓
api-gateway generates task_id = "abc-123"
  ↓
make_event("abc-123", "research.created", "api-gateway", {"query": "..."})
  → {"task_id": "abc-123", "event": "research.created", "service": "api-gateway", ...}
  ↓
publish_event("research.created", event)
  → AIOKafkaProducer.send_and_wait("research.created", value=bytes, key=b"abc-123")
  ↓
orchestrator consumer receives the message
  → json.loads(msg.value)
  → asyncio.create_task(run_workflow("abc-123", "..."))
```

> [!note]
> Topics in Kafka are created automatically the first time a producer writes to them. You don't need to `CREATE TOPIC` manually when using Redpanda in dev mode. In production Kafka, you'd pre-create topics with specific partition counts and replication factors.
