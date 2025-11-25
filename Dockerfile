# Multi-stage Dockerfile for QnA Agent API
# Stage 1: Builder - Install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock poetry.toml ./

# Configure poetry to create virtualenv in project and install dependencies
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi --only main --no-root

# Stage 2: Runner - Minimal runtime image
FROM python:3.12-slim AS runner

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1001 appuser

WORKDIR /app

# Install poetry in runner stage
RUN pip install --no-cache-dir poetry

# Copy virtualenv and poetry config from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/poetry.lock /app/poetry.toml ./

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY knowledge/ ./knowledge/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create data directory for SQLite with proper permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Expose application port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# Ensure working directory is set
WORKDIR /app
