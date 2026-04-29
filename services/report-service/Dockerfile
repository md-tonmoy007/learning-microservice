FROM python:3.11-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
COPY services/ ./services/
COPY shared/ ./shared/
RUN uv sync --frozen --no-dev --no-cache --package report-service

WORKDIR /workspace/services/report-service

EXPOSE 50055
CMD ["uv", "run", "--package", "report-service", "python", "-m", "app.main"]
