# Dockerfile for Geospatial AI Co-Scientist
# Multi-stage build for optimized production image

# =============================================================================
# STAGE 1: Builder
# Install dependencies and build wheels
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /build

# Install build dependencies (only in builder stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency specification
COPY pyproject.toml ./

# Install dependencies into the virtual environment
RUN pip install --upgrade pip wheel setuptools && \
    pip install .

# =============================================================================
# STAGE 2: Runtime
# Minimal production image with only runtime dependencies
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Application settings
    GEO_SCIENTIST_LOG_LEVEL=INFO

WORKDIR /app

# Install only runtime system dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gdal-bin \
    libgdal32 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY src/ ./src/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 scientist && \
    chown -R scientist:scientist /app

USER scientist

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run FastAPI server
CMD ["python", "-m", "uvicorn", "geospatial_co_scientist.ui.api:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# STAGE 3: Development (optional)
# Full development environment with dev dependencies
# =============================================================================
FROM runtime AS development

USER root

# Install dev dependencies
COPY pyproject.toml ./
RUN pip install -e ".[dev]"

# Copy test files
COPY tests/ ./tests/

# Switch back to non-root user
USER scientist

# Override command for development
CMD ["python", "-m", "uvicorn", "geospatial_co_scientist.ui.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
