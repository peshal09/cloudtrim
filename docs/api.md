# API reference

The API is FastAPI, versioned under `/api/v1`. Interactive docs and the schema are
served live:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI schema:** `http://localhost:8000/openapi.json` (a committed copy is at
  [`docs/openapi.json`](openapi.json) — regenerate with
  `python scripts/export_openapi.py`)

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/analyses` | Analyze uploaded Terraform / Kubernetes / billing (sync, or enqueue in async mode). |
| POST | `/api/v1/analyses/sample` | Run the bundled demo dataset (no upload). |
| GET | `/api/v1/analyses/{id}` | Status + savings summary. |
| GET | `/api/v1/analyses/{id}/findings` | Findings, sorted by savings then severity. |
| GET | `/api/v1/analyses/{id}/summary` | Aggregate: realistic (deduped) vs gross savings, top ops. |
| GET | `/api/v1/analyses/{id}/narrative` | Architect-voice prioritization narrative. |
| GET | `/api/v1/analyses/{id}/report.md` · `/report.pdf` | Exportable report. |
| GET | `/api/v1/findings/{id}` | Single finding + its resource. |
| GET | `/api/v1/trends` | Savings over time (one point per analysis). |
| POST | `/api/v1/anomalies` · `/anomalies/sample` | Cost anomaly detection + forecast. |
| POST | `/api/v1/github/webhook` | GitHub App webhook (HMAC-verified). |
| GET | `/api/v1/healthz` | Liveness. |
| GET | `/metrics` | Prometheus metrics (unversioned, unauthenticated). |

## Auth

Open by default. When `CLOUDTRIM_API_KEYS` is set, `/api/v1/analyses*`, `/findings*`,
`/trends`, and `/anomalies*` require `Authorization: Bearer <key>` (or `X-API-Key`).
`/healthz`, `/metrics`, and the HMAC-verified webhook are always open. See
[`operations.md`](operations.md).
