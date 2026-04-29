---
tags: [phase-1, docker, compose, infrastructure]
file: docker-compose.yml
---

# Docker and Compose

> How each service is containerised and how Docker Compose wires them together into a runnable system.

Related: [[Project Structure]] · [[API Gateway]] · [[LangGraph Orchestrator]] · [[PostgreSQL Models]] · [[Home]]

---

## The Code

**Dockerfiles:** `services/api-gateway/Dockerfile` · `services/orchestrator/Dockerfile`
**Compose file:** `docker-compose.yml`

---

## Walkthrough

### The api-gateway Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml ./
RUN uv sync --frozen --no-dev --no-cache

COPY app/ ./app/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Line by line:**

`FROM python:3.11-slim` — minimal Python 3.11 base image. `slim` drops documentation, tests, and extra locale data that are not needed at runtime. Saves ~100 MB vs the full image.

`COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv` — copies the `uv` binary from the official uv image into `/bin/uv`. This is a multi-stage trick: we don't install uv via pip, we just copy the pre-built binary. Fast and minimal.

`COPY pyproject.toml ./` then `RUN uv sync --frozen --no-dev --no-cache` — installs dependencies from the lockfile before copying source code. This is a **layer caching** trick: if only the source code changes (not `pyproject.toml`), Docker reuses the cached dependency layer and skips the install. `--frozen` refuses to update the lockfile. `--no-dev` skips dev dependencies. `--no-cache` prevents uv from caching packages inside the image.

`COPY app/ ./app/` — copies source code. Comes after the dependency install so a code-only change doesn't re-trigger the slow `uv sync` layer.

`EXPOSE 8000` — documents which port the container listens on. Does not actually publish the port — that's done in `docker-compose.yml`.

`CMD ["uv", "run", "uvicorn", ...]` — starts the server. `--host 0.0.0.0` is required inside Docker: the default `127.0.0.1` only listens inside the container, not on the Docker network interface.

### The orchestrator Dockerfile — what's different

```dockerfile
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
```

The orchestrator installs `curl` because the health check in `docker-compose.yml` calls `curl -f http://localhost:8001/health`. The gateway doesn't need this because its health is checked by the api-gateway itself being up.

```dockerfile
COPY alembic/ ./alembic/
COPY alembic.ini ./
```

The orchestrator copies the Alembic migration directory too. The gateway has no DB and no migrations.

---

### docker-compose.yml — the full picture

```yaml
services:
  api-gateway:
    build:
      context: services/api-gateway
    ports:
      - "8000:8000"
    environment:
      ORCHESTRATOR_URL: http://orchestrator:8001
    depends_on:
      orchestrator:
        condition: service_healthy
    restart: on-failure

  orchestrator:
    build:
      context: services/orchestrator
    ports:
      - "8001:8001"
    environment:
      POSTGRES_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/research
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      OPENROUTER_MODEL: ${OPENROUTER_MODEL:-z-ai/glm-4.5-air:free}
      TAVILY_API_KEY: ${TAVILY_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: on-failure

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: research
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Service networking — how containers find each other

Docker Compose puts all services on a shared virtual network. Each service is reachable by its **service name** as a hostname:

```
orchestrator calls postgres at: postgresql+asyncpg://postgres:postgres@postgres:5432/research
                                                                          ↑
                                                               service name = DNS hostname
api-gateway calls orchestrator at: http://orchestrator:8001
                                          ↑
                                 service name = DNS hostname
```

This is why `settings.orchestrator_url` defaults to `http://orchestrator:8001` — that's the Docker DNS name, not `localhost`.

### `depends_on` with `condition: service_healthy`

```yaml
depends_on:
  orchestrator:
    condition: service_healthy
```

`depends_on` without a condition only waits for the container to start. With `condition: service_healthy`, Docker waits until the health check passes before starting the dependent service. This matters because:
- The orchestrator needs a few seconds to start uvicorn
- The api-gateway would otherwise crash immediately trying to connect to a not-yet-ready orchestrator

The health check on the orchestrator:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
  interval: 10s   # check every 10s
  timeout: 5s     # declare unhealthy if no response in 5s
  retries: 5      # fail after 5 consecutive failures
  start_period: 10s  # don't count failures for the first 10s after start
```

`start_period` gives the service time to boot before Docker starts counting failures.

### `${OPENROUTER_API_KEY}` - reading from the host environment

```yaml
environment:
  OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
  OPENROUTER_MODEL: ${OPENROUTER_MODEL:-z-ai/glm-4.5-air:free}
```

Docker Compose reads `${VAR}` from the host shell environment or from a `.env` file at the project root. This keeps secrets out of the compose file itself. Copy `.env.example` to `.env` and fill in your keys — Docker Compose picks it up automatically.

### Named volume — `postgres_data`

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Named volumes survive `docker compose down`. The postgres data is not lost when you stop the stack. To wipe the database completely:
```bash
docker compose down -v   # -v removes named volumes
```

### `restart: on-failure`

If a service crashes (non-zero exit code), Docker restarts it automatically. This catches transient startup failures like "couldn't connect to postgres yet." It does **not** restart on a clean exit (exit code 0).

---

## Workflow

```bash
# First time setup
cp .env.example .env          # fill in OPENROUTER_API_KEY, TAVILY_API_KEY
docker compose up --build     # build images and start everything

# Run migrations (first time only, after postgres is healthy)
docker compose exec orchestrator uv run alembic upgrade head

# Day-to-day
docker compose up             # start (no rebuild)
docker compose down           # stop, keep volumes
docker compose down -v        # stop, wipe volumes (fresh DB)
docker compose logs -f orchestrator   # tail logs for one service
docker compose restart orchestrator   # restart one service

# Rebuild only one service after code change
docker compose up --build orchestrator
```

> [!tip] Layer caching saves time
> After the first build, subsequent `--build` calls skip the `uv sync` layer if `pyproject.toml` didn't change. Only the `COPY app/` layer re-runs. A code-only change rebuilds in seconds, not minutes.

> [!warning] Migrations are not automatic
> The Dockerfile does not run `alembic upgrade head` on startup. This is intentional — you don't want migrations running automatically in production. Run them manually after the first start, or before each deployment.

> [!note] Phase 2 addition
> In Phase 2, `docker-compose.yml` will gain five more services: `planner-agent`, `search-agent`, `summarizer-agent`, `critic-agent`, `report-service`. Each will have a gRPC port instead of HTTP.
