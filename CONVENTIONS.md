# CloudTrim — Working Conventions

## The one law
The engine is authoritative; the LLM is a narrator. Parsing, detection, pricing,
risk, and remediation are 100% deterministic. The LLM only explains and prioritizes,
and its output is validated against engine numbers (regenerate on mismatch). Never
let the model compute or assert a dollar figure.

## Structure
Monorepo: `apps/{api,worker,web}`, `packages/{engine,ai}`, `eval/`, `infra/`, `docs/`.
Business logic lives in `packages/engine` — the API and worker are thin.

Python imports resolve via `PYTHONPATH` (see the `Makefile` and `pyproject.toml`
`[tool.pytest.ini_options].pythonpath`), not an editable install, while the repo is
a scaffold: `api`, `worker`, `engine`, `ai` are the importable top-level packages.

## Conventions
- Python: FastAPI, ruff + black, pytest. Type hints everywhere.
- Every detector: its own file in `packages/engine/engine/detectors` + a unit test + registry entry.
- Every dollar figure traces to `packages/engine/engine/pricing`. No magic numbers.
- Commit after each green step; small, reviewable commits.
- New architectural decisions → an ADR in `docs/adr/`.
- `docs/BLUEPRINT.md` is the spec. If unsure, re-read the relevant section before coding.

## Common commands
- `make lint` / `make format` — ruff + black
- `make test` — pytest
- `make run` — uvicorn (API on :8000, `/api/v1/healthz`)
- `make eval` — eval harness (stub until Week 2)
- `cd apps/web && npm install && npm run dev` — web on :3000

## Definition of done (per feature)
Code + unit tests passing + lint clean + docs/README updated if user-facing +
eval still green.
