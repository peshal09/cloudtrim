# Operations

Running, configuring, observing, and scaling CloudTrim.

## Configuration

All settings are environment variables prefixed `CLOUDTRIM_` (see `.env.example`).
Everything external is **opt-in** — with nothing set, the API runs synchronously
against an in-memory store with the deterministic template explainer and no keys.

| Variable | Effect |
|---|---|
| `CLOUDTRIM_DATABASE_URL` | Postgres persistence (async path). e.g. `postgresql+psycopg://…` |
| `CLOUDTRIM_REDIS_URL` | RQ broker. Setting this **and** the DB enables async enqueue → worker. |
| `CLOUDTRIM_LLM_API_KEY` | Use the LLM for explanations/narrative (else template). |
| `CLOUDTRIM_LLM_MODEL` | Model id for the LLM endpoint. |
| `CLOUDTRIM_API_KEYS` | Comma-separated keys → enables API-key auth. |
| `CLOUDTRIM_RATE_LIMIT_PER_MINUTE` | > 0 → per-client rate limiting. |
| `CLOUDTRIM_CACHE_TTL_SECONDS` | Explanation cache TTL (default 3600; 0 = no expiry). |
| `CLOUDTRIM_GITHUB_WEBHOOK_SECRET`, `CLOUDTRIM_GITHUB_TOKEN` | GitHub App (see `github-app.md`). |
| `CLOUDTRIM_CORS_ORIGINS` | Browser origins allowed to call the API. |

## Running

```bash
make run                 # sync, in-memory (no deps)
docker compose up        # full async stack: api + worker + web + redis + postgres
CLOUDTRIM_DATABASE_URL=... make seed   # seed the demo analysis into the DB
```

In async mode, `POST /analyses` returns a **pending** record; the worker fills it in
and the client polls `GET /analyses/{id}` until `status: complete`. Apply migrations
with `alembic upgrade head` (the API also `create_all`s on boot for dev convenience).

## Deploy (Fly.io)

```bash
fly launch --copy-config --no-deploy      # uses fly.toml (API)
fly postgres create && fly postgres attach # sets CLOUDTRIM_DATABASE_URL
fly secrets set CLOUDTRIM_REDIS_URL=<upstash-url> CLOUDTRIM_API_KEYS=<keys>
fly deploy                                 # API
# Worker: a second app from apps/worker/Dockerfile, same secrets, no http_service.
```

CI deploys on merge to `main` when `FLY_API_TOKEN` is set as a repo secret (the
deploy job skips cleanly otherwise).

## Observability

- **Logs** — structured JSON on stdout, one line per request, with `request_id`,
  method, route template, status, and `duration_ms`.
- **Request IDs** — every response carries `X-Request-ID`; supply one to correlate.
- **Metrics** — `GET /metrics` (Prometheus text, unauthenticated):
  `cloudtrim_http_requests_total`, `…_request_duration_seconds_sum` (by route
  template), and `cloudtrim_llm_*` (calls, tokens, estimated cost).
- **Errors** — consistent `{"error": {type, message, request_id}}` envelope.

## Scaling notes

- **Workers** — scale RQ workers horizontally; jobs are idempotent (pre-assigned id
  + replacing save), so retries and redeliveries converge.
- **Stateless API** — scale the API behind a load balancer; all state is in Postgres.
- **Known single-replica caveats** — the rate limiter and webhook idempotency set are
  in-memory; move both to a shared Redis counter/set before running multiple API
  replicas.
- **Caching** — pricing is a committed snapshot + disk cache (no network on the hot
  path); LLM responses are cached with a TTL.

## Runbook

| Symptom | Check |
|---|---|
| Analysis stuck `pending` | Worker running? `docker compose logs worker`; Redis reachable? |
| `503` from `/analyses` | (async) DB/Redis down, or GitHub webhook without `CLOUDTRIM_GITHUB_TOKEN`. |
| `401` on every request | `CLOUDTRIM_API_KEYS` set — send `Authorization: Bearer <key>`. |
| `429` | Rate limit hit; raise `CLOUDTRIM_RATE_LIMIT_PER_MINUTE` or back off. |
| Savings look wrong | `make eval` (100% on the labeled benchmark); the snapshot pins numbers. |
| PR bot silent | Signature mismatch (check the webhook secret) or token lacks scopes. |
