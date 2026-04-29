FROM python:3.11-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
COPY services/ ./services/
COPY shared/ ./shared/
RUN uv sync --frozen --no-dev --no-cache --package summarizer-agent

WORKDIR /workspace/services/summarizer-agent

EXPOSE 50053
CMD ["uv", "run", "--package", "summarizer-agent", "python", "-m", "app.main"]
