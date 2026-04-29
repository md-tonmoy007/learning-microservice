FROM python:3.11-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
COPY services/ ./services/
COPY shared/ ./shared/
RUN uv sync --frozen --no-dev --no-cache --package api-gateway

WORKDIR /workspace/services/api-gateway

EXPOSE 8000
CMD ["uv", "run", "--package", "api-gateway", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
