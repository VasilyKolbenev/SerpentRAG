# ─────────────────────────────────────────────
# SERPENT RAG PLATFORM — Backend Dockerfile
# Multi-stage build with security hardening
# ─────────────────────────────────────────────

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production
FROM python:3.12-slim AS production

# Security: Create non-root user
RUN groupadd -r serpent && useradd -r -g serpent -d /app -s /sbin/nologin serpent

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# Copy Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY --chown=serpent:serpent . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/models /app/logs && \
    chown -R serpent:serpent /app

# Entrypoint: run Alembic migrations before starting
RUN chmod +x /app/entrypoint.sh

# Security headers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Health check managed by docker-compose

# Switch to non-root user
USER serpent

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
