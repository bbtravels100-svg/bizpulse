# syntax=docker/dockerfile:1
# ==============================================================================
# BizPulse Backend - Production Multi-Stage Dockerfile
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Hardened Unprivileged Runner
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production \
    DATA_DIR=/app/data \
    DATABASE_PATH=/app/data/bizpulse.db \
    BACKUP_DIR=/app/data/backups

# Install curl for reliable container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application system user and group (UID 10001)
RUN groupadd -g 10001 bizpulse && \
    useradd -u 10001 -g bizpulse -s /bin/bash -m bizpulse

# Copy pre-compiled virtual environment from builder stage
COPY --from=builder --chown=bizpulse:bizpulse /opt/venv /opt/venv

# Prepare writable storage directories for SQLite, WAL files, backups, and datasets
RUN mkdir -p /app/data/backups && \
    chown -R bizpulse:bizpulse /app

# Copy application source code
COPY --chown=bizpulse:bizpulse app/ /app/app/
# Seed default business datasets (sales, costs, funnel, events)
COPY --chown=bizpulse:bizpulse data/*.csv /app/data/

# Switch permanently to unprivileged user
USER bizpulse:bizpulse

# Expose backend service port
EXPOSE 8000

# Container healthcheck using public minimal health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production ASGI server with signal handling and graceful shutdown
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
