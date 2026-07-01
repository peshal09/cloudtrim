FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching. [db,queue] enables the async path;
# [reports] the PDF export.
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[db,queue,reports]"

# Source (packages are imported via PYTHONPATH; scaffold has no editable install).
COPY apps/api ./apps/api
COPY packages ./packages
COPY scripts ./scripts

ENV PYTHONPATH=/app/apps/api:/app/packages/engine:/app/packages/ai

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
