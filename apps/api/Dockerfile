FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching.
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]" || pip install --no-cache-dir \
    "fastapi>=0.115" "uvicorn[standard]>=0.32" "pydantic>=2.9" \
    "pydantic-settings>=2.6" "python-multipart>=0.0.12"

# Source (packages are imported via PYTHONPATH; scaffold has no editable install).
COPY apps/api ./apps/api
COPY packages ./packages

ENV PYTHONPATH=/app/apps/api:/app/packages/engine:/app/packages/ai

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
