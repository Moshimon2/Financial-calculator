# syntax=docker/dockerfile:1
# fincalc - multi-stage build: dependencies are installed with uv in a builder
# stage, the runtime image only gets the virtualenv and the application files.

ARG PYTHON_IMAGE=python:3.12-slim

# --- builder ------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder

RUN pip install --no-cache-dir "uv==0.11.32"

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Dependencies first (cached layer as long as the lock file is unchanged).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the project itself (editable install: /app/src stays the import path,
# so config/ and alembic.ini next to it are found).
COPY README.md alembic.ini ./
COPY src ./src
COPY config ./config
COPY migrations ./migrations
RUN uv sync --frozen --no-dev

# --- runtime ------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

LABEL org.opencontainers.image.title="fincalc" \
      org.opencontainers.image.description="Self-hosted financial calculator for Hungarian investors" \
      org.opencontainers.image.source="https://github.com/Moshimon2/Financial-calculator"

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FINCALC_DATABASE_URL="sqlite:////app/data/fincalc.db" \
    FINCALC_TIMEZONE="Europe/Budapest" \
    FINCALC_LOG_LEVEL="info"

# Non-root user. The UID/GID can be overridden at runtime (compose `user:`),
# the image does not depend on it: app files are read-only, data lives in /app/data.
RUN groupadd --system --gid 1000 fincalc \
    && useradd --system --uid 1000 --gid fincalc --no-create-home --home-dir /app fincalc \
    && mkdir -p /app/data \
    && chown fincalc:fincalc /app/data

WORKDIR /app
COPY --from=builder /app /app

USER fincalc
EXPOSE 8000
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"]

# Alembic migrations run on application start-up (FINCALC_AUTO_MIGRATE=0 disables).
CMD ["sh", "-c", "exec uvicorn fincalc.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --log-level \"${FINCALC_LOG_LEVEL}\""]
