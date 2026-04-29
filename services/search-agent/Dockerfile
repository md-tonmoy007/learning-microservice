FROM python:3.11-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
COPY services/ ./services/
COPY shared/ ./shared/
RUN uv sync --frozen --no-dev --no-cache --package search-agent

WORKDIR /workspace/services/search-agent

EXPOSE 50052
CMD ["uv", "run", "--package", "search-agent", "python", "-m", "app.main"]
