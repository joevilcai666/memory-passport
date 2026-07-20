# Memory Passport backend image.
# python:3.11-slim matches the HMS base image so the compose stack is uniform.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl is required by the docker-compose healthcheck (curl /v1/health).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the package first so dependency layers cache independently of source.
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --upgrade pip && pip install -e ".[dev]"

# Non-root runtime.
RUN useradd --create-home --shell /usr/sbin/nologin mp \
    && chown -R mp:mp /app
USER mp

EXPOSE 8000

# Default: run the API server. docker-compose overrides this for --reload in dev.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
