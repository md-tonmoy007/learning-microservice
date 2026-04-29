FROM python:3.11-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
COPY services/ ./services/
COPY shared/ ./shared/
RUN uv sync --frozen --no-dev --no-cache --package critic-agent

WORKDIR /workspace/services/critic-agent

EXPOSE 50054
CMD ["uv", "run", "--package", "critic-agent", "python", "-m", "app.main"]
