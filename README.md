# CloudTrim

> **A shift-left cloud cost optimizer that reviews your Terraform, Kubernetes manifests, and billing data like a senior cloud architect** — detecting waste and anti-patterns with a deterministic engine, pricing the impact against live cloud pricing, and opening explained, risk-scored, ready-to-merge fix PRs in CI.

Not a dashboard. A **reviewer that remediates.**

## The gap it fills

| Existing tools | What they miss |
|---|---|
| Cost Explorer / Compute Optimizer | Show savings, don't execute changes; opaque one-liners; no IaC awareness |
| Kubecost / OpenCost | Allocation/monitoring; terse or zero recommendations |
| CAST AI | Fixes things — but only by taking over your cluster and auto-executing |
| Infracost | Prices a Terraform PR, but tells you the price, not the waste or the fix |

CloudTrim closes three gaps none of them fill together: **reasoning** (explains like an architect), **remediation** (hands you a safe, reviewable fix PR), and **cross-signal correlation** (config + billing + cluster in one model).

## The one law

The **engine is authoritative; the LLM is a narrator.** Parsing, detection, pricing, risk, and remediation are 100% deterministic. The LLM only explains and prioritizes, and its output is validated against engine numbers — it can't hallucinate a dollar figure. See [`docs/adr/0001-deterministic-core-llm-explains.md`](docs/adr/0001-deterministic-core-llm-explains.md).

## Status

🚧 **Scaffold.** Structure, tooling, and a health endpoint are in place; feature work (parsers, detectors, pricing, AI explainer, dashboard) begins with the Week 1 MVP. See [`docs/BLUEPRINT.md`](docs/BLUEPRINT.md) for the full spec and six-week roadmap.

## Quickstart

**API (Python 3.12):**

```bash
make install        # pip install -e ".[dev]"
make test           # pytest
make run            # uvicorn -> http://localhost:8000/api/v1/healthz
```

**Web (Node):**

```bash
cd apps/web
npm install
npm run dev         # http://localhost:3000
```

**Or via Docker Compose:**

```bash
cp .env.example .env
docker compose up --build   # api :8000, web :3000
```

## Structure

```
apps/{api,worker,web}   # FastAPI edge · async worker (Week 3) · Next.js UI
packages/{engine,ai}    # deterministic engine · bounded LLM layer
eval/                   # labeled fixtures + precision/recall harness (Week 2)
infra/  docs/           # deploy manifests · spec, ADRs, architecture
```

## Tech stack

Python + FastAPI · Redis/Celery worker pool (Week 3) · Postgres (Week 3) · Next.js + Tailwind · AWS Price List pricing · LLM/OpenAI (explanation only, validated).
