FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching (engine, ai, db, queue).
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[db,queue]" || pip install --no-cache-dir \
    "python-hcl2>=4.3" "pyyaml>=6.0" "pydantic>=2.9" "sqlalchemy>=2.0" \
    "psycopg[binary]>=3.2" "rq>=1.16" "redis>=5.0"

# The worker runs the pipeline (engine + ai) and persists via the API's store layer.
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
COPY packages ./packages

ENV PYTHONPATH=/app/apps/worker:/app/apps/api:/app/packages/engine:/app/packages/ai

# Consume the analysis queue. CLOUDTRIM_REDIS_URL + CLOUDTRIM_DATABASE_URL must be set.
# Shell form so the env var expands.
CMD rq worker cloudtrim --url "$CLOUDTRIM_REDIS_URL"
