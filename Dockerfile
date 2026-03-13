# ============================================================
# FlowZone Dockerfile
# Multi-stage build for small image size
# Compatible with Railway, Render, AWS ECS
# ============================================================

# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies for packages that need compilation
# (asyncpg, sentence-transformers, chromadb, pymupdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: Runtime ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user (security best practice)
RUN useradd --create-home --shell /bin/bash flowzone

# Create data directories
RUN mkdir -p /app/data/chromadb /app/data/uploads && \
    chown -R flowzone:flowzone /app

# Copy application code
COPY . .

# Switch to non-root user
USER flowzone

# Expose port (Railway auto-detects this)
EXPOSE 8000

# Health check (Railway and Docker both use this)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
# --workers 1 is fine for 5 concurrent users on Railway's small instances
# Scale workers when moving to AWS ECS
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
