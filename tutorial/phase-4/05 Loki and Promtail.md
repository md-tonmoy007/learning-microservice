---
tags: [phase-4, loki, promtail, logging, logql]
file: config/promtail.yaml
---

# 05 Loki and Promtail

> Promtail reads every container's stdout via the Docker socket and ships it to Loki. Because every service already emits structured JSON logs, Loki can parse and label them — making logs filterable by `task_id`, `level`, and `service` without any code changes.

Related: [[01 Observability Overview]] · [[04 Grafana Dashboards]] · [[Home]]

---

## The Code

### Promtail config (`config/promtail.yaml`)

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker-containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ["__meta_docker_container_label_com_docker_compose_service"]
        target_label: service
      - source_labels: ["__meta_docker_container_name"]
        regex: "/(.*)"
        target_label: container
    pipeline_stages:
      - json:
          expressions:
            level: level
            task_id: task_id
      - labels:
          level:
          task_id:
```

### Loki config (`config/loki.yaml`)

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
```

### docker-compose additions

```yaml
loki:
  image: grafana/loki:latest
  ports:
    - "3100:3100"
  volumes:
    - ./config/loki.yaml:/etc/loki/local-config.yaml
    - loki_data:/loki
  command: -config.file=/etc/loki/local-config.yaml

promtail:
  image: grafana/promtail:latest
  volumes:
    - ./config/promtail.yaml:/etc/promtail/config.yml
    - /var/run/docker.sock:/var/run/docker.sock
  command: -config.file=/etc/promtail/config.yml
  depends_on:
    - loki
```

---

## Walkthrough

### How Promtail finds the logs

Promtail uses **Docker service discovery** (`docker_sd_configs`). It connects to the Docker socket (`/var/run/docker.sock`) and asks Docker for the list of running containers. For each container it finds, it tails that container's log stream — the same stream you see with `docker logs`.

```
docker.sock → list containers → [api-gateway, orchestrator, planner-agent, ...]
            → tail each container's stdout/stderr
            → apply relabeling and pipeline stages
            → batch log lines → push to Loki
```

The volume mount `/var/run/docker.sock:/var/run/docker.sock` gives the Promtail container access to the host's Docker socket. This works on Docker Desktop for Windows via the WSL2 layer.

### Relabeling — how service labels are set

Docker Compose sets metadata labels on every container it starts. One of them is:
```
com.docker.compose.service = "orchestrator"
```

The relabeling rule copies that Docker metadata label to a Loki log label called `service`:

```yaml
relabel_configs:
  - source_labels: ["__meta_docker_container_label_com_docker_compose_service"]
    target_label: service
```

After relabeling, every log line from the orchestrator container has `{service="orchestrator"}` attached. You can then query all orchestrator logs with `{service="orchestrator"}` in Grafana.

### Pipeline stages — parsing the JSON

Every service already outputs structured JSON via `shared/logging.py`:
```json
{"timestamp":"2026-04-30T10:31:00Z","level":"INFO","service":"orchestrator","message":"Published research.planned for task abc-123","task_id":"abc-123"}
```

The pipeline stage parses that JSON and promotes `level` and `task_id` into Loki labels:

```yaml
pipeline_stages:
  - json:
      expressions:
        level: level
        task_id: task_id
  - labels:
      level:
      task_id:
```

After this, each log line has labels `{service="orchestrator", level="INFO", task_id="abc-123"}`. You can search for all logs related to a specific task across all services.

### Why labels matter in Loki

Loki is not Elasticsearch. It does **not** index the full text of log lines. Instead, it indexes only the **labels**. The log line content is stored compressed and searched at query time.

This means:
- Label queries (`{service="orchestrator"}`) are fast — they use the index
- Full-text search (`|= "abc-123"`) works but scans the log stream — slower
- Keeping the label set small is important — too many high-cardinality labels (like URLs) bloat the index

`task_id` is moderate cardinality (one per research task) and extremely useful for cross-service correlation, so it is worth indexing as a label.

### `positions.yaml` — why Promtail needs it

```yaml
positions:
  filename: /tmp/positions.yaml
```

Promtail tracks how far it has read each log stream in a file called `positions.yaml`. If Promtail restarts, it resumes from where it left off instead of re-sending all old log lines.

Without this: every Promtail restart would re-deliver all container logs to Loki. With it: resumption is seamless.

---

## Querying Logs in Grafana

Open Grafana → Explore → select **Loki** datasource.

### LogQL basics

```logql
# All logs from the orchestrator
{service="orchestrator"}

# All ERROR logs across all services
{service=~".+"} | json | level="ERROR"

# All logs for a specific task, any service
{task_id="abc-123"}

# Orchestrator logs containing a specific word
{service="orchestrator"} |= "Workflow failed"

# Count errors per service per minute
sum by (service) (rate({service=~".+"} | json | level="ERROR" [1m]))
```

### Cross-service trace for one task

```logql
{task_id="abc-123"}
```

This single query returns every log line from every service that logged with `task_id="abc-123"` — gateway, orchestrator, all agents — in chronological order. That's the full story of one research task in one view.

---

## Workflow

```
docker compose up
  → Loki starts, listens on :3100
  → Promtail starts, connects to docker.sock
  → Promtail discovers all running containers
  → Promtail tails each container's log stream

Orchestrator logs: {"level":"INFO","task_id":"abc-123","message":"Published research.planned"}
  → Promtail reads line
  → pipeline_stages: parses JSON, extracts level="INFO", task_id="abc-123"
  → attaches labels: {service="orchestrator", level="INFO", task_id="abc-123"}
  → ships to Loki: POST loki:3100/loki/api/v1/push

Grafana → Explore → Loki:
  {task_id="abc-123"}  → returns all lines tagged with that task, across all services
```

> [!warning]
> On Windows with Docker Desktop, Promtail's access to `/var/run/docker.sock` depends on Docker Desktop exposing the socket. If Promtail fails to start with a "no such file or directory" error on the socket, check **Docker Desktop → Settings → General → Expose daemon on tcp://localhost:2375** (not recommended) or ensure the WSL2 socket is forwarded. The default Docker Desktop setup should work with the socket mount as configured.

> [!tip]
> If logs aren't appearing in Loki, check Promtail's own logs first: `docker compose logs promtail`. Common issues: Promtail can't reach Loki (wrong URL), or the Docker socket isn't accessible.
