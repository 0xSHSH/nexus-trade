# ─────────────────────────────────────────────────────────────────────────────
#  NexusTrade — Production Dockerfile
#  Multi-stage build: keeps the final image lean (~200MB vs ~800MB).
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build tools for native extensions (cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash nexustrade
WORKDIR /home/nexustrade/app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=nexustrade:nexustrade app/ ./app/

USER nexustrade

EXPOSE 8000

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
