FROM python:3.11-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY services/ ./services/
COPY shared/ ./shared/
RUN uv sync --frozen --no-dev --no-cache --package orchestrator

WORKDIR /workspace/services/orchestrator

EXPOSE 8001
CMD ["uv", "run", "--package", "orchestrator", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
