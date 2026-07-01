FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching.
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]" || pip install --no-cache-dir \
    "fastapi>=0.115" "pydantic>=2.9" "pydantic-settings>=2.6" "python-hcl2>=4.3"

# Source (packages imported via PYTHONPATH; scaffold has no editable install).
COPY apps/worker ./apps/worker
COPY packages ./packages

ENV PYTHONPATH=/app/apps/worker:/app/packages/engine:/app/packages/ai

# The async job worker (Redis + RQ/Celery consuming analysis jobs) lands in Week 3
# (see docs/BLUEPRINT.md §3). This image is ready for it.
CMD ["python", "-c", "print('CloudTrim worker image — job processing arrives in Week 3')"]
