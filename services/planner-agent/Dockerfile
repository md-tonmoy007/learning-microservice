FROM python:3.11-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
COPY services/ ./services/
COPY shared/ ./shared/
RUN uv sync --frozen --no-dev --no-cache --package planner-agent

WORKDIR /workspace/services/planner-agent

EXPOSE 50051
CMD ["uv", "run", "--package", "planner-agent", "python", "-m", "app.main"]
