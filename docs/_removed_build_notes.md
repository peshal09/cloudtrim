# CloudTrim — LLM Code Kickoff Guide

How to start and drive the build with LLM Code. Copy the prompts verbatim.

---

## Step 0 — Set up (do this once, in your terminal)

```bash
mkdir cloudtrim && cd cloudtrim
git init
mkdir docs
# copy the blueprint into the repo so LLM Code can read it as the source of truth
cp /path/to/CloudTrim_Engineering_Blueprint.md docs/BLUEPRINT.md
LLM            # start LLM Code inside the repo
```

Working rules that keep LLM Code effective:
- **One milestone per session.** Don't ask it to "build the whole project." Build Week 1, review, commit, then start a fresh session for Week 2.
- **Make it plan before it codes.** Ask for a plan first, approve it, then let it implement.
- **Commit after every green step.** Small commits = easy to review and revert.
- **Tests are non-negotiable per feature.** The eval harness and unit tests are your credibility; make LLM write them as it goes, not at the end.
- **BLUEPRINT.md is the contract.** When LLM drifts, say "re-read docs/BLUEPRINT.md section N and align."

---

## Step 1 — Bootstrap prompt (first message to LLM Code)

> Read `docs/BLUEPRINT.md` fully — it is the authoritative spec for this project. Then bootstrap the repository *scaffold only* (no feature logic yet):
>
> 1. Create the monorepo structure exactly as in Section 8 (`apps/api`, `apps/worker`, `apps/web`, `packages/engine`, `packages/ai`, `eval`, `infra`, `docs`).
> 2. Set up Python tooling for the backend: `pyproject.toml` (or `requirements.txt`), `ruff` + `black` for lint/format, `pytest` configured, and a `Makefile` with `lint`, `test`, `run`, `eval` targets.
> 3. Scaffold FastAPI in `apps/api` with a `/api/v1/healthz` endpoint and versioned router, running via `uvicorn`.
> 4. Scaffold the Next.js app in `apps/web` (TypeScript + Tailwind) with an empty upload page.
> 5. Add `docker-compose.yml` with `api` and `web` services (Redis/Postgres commented out for now, added in Week 3).
> 6. Create a `LLM.md` at the repo root capturing the conventions below (see "LLM.md" section of this guide) so future sessions stay consistent.
> 7. Create `.gitignore`, a stub `README.md` (pull the one-liner + gap table from the blueprint), and `docs/adr/0001-deterministic-core-llm-explains.md` recording the "engine computes, LLM narrates, output validated" decision.
>
> Do NOT implement detectors, pricing, or AI yet. Show me the plan first, wait for my approval, then scaffold. After scaffolding, verify `make lint` and `make test` pass and `healthz` returns 200.

---

## Step 2 — MVP prompt (second session, after scaffold is committed)

> Re-read `docs/BLUEPRINT.md` Sections 2 (MVP) and 6 (AI Architecture). Implement the Week 1 MVP. Follow the deterministic-core law strictly: the engine computes every dollar figure; the LLM only explains; validate the LLM's cited numbers against the engine and regenerate on mismatch.
>
> Build in this order, committing after each step passes tests:
> 1. **Parsers** (`packages/engine/parsers`): Terraform (`terraform show -json` primary, `python-hcl2` fallback) and billing CSV → a normalized `Resource` model. Unit tests against fixtures.
> 2. **Normalizer**: merge config + billing into one ResourceModel keyed by identifier/tags.
> 3. **Detector registry** + the 6 MVP detectors from Section 2. Each detector is its own file, independently unit-tested, and emits a `Finding` + candidate remediation.
> 4. **Pricing engine** (`packages/engine/pricing`): AWS Price List bulk JSON, cached to disk; compute current vs projected cost → savings. Tests: known instance → known price.
> 5. **Risk scorer**: deterministic Low/Med/High.
> 6. **API**: the four `/api/v1` endpoints from Section 2, backed by the engine (synchronous for now; async queue comes in Week 3).
> 7. **AI explainer** (`packages/ai`): `explain_finding()` with structured output, the validation step, and retry/fallback + caching.
> 8. **Web**: upload page (with a "load sample data" button), findings dashboard (savings hero + severity breakdown + table), and a finding-detail drawer showing evidence, proposed change, risk badge, and explanation.
>
> Also create `eval/fixtures` with 3–4 labeled known-waste samples so I can demo instantly. Plan first, then implement. End by confirming the full flow works end-to-end on the sample data.

---

## Step 3 — Per-week driver prompt (reuse for Weeks 2–6)

Swap in the week number each time:

> Re-read `docs/BLUEPRINT.md` Section 3 → **Week N**. Implement every checkbox under Backend, Frontend, AI, Infrastructure, Testing, Documentation, and Deployment for that week. Keep the deterministic-core law. Show me a plan mapped to those checkboxes first; after approval, implement step-by-step with a passing test and a commit after each. At the end, tick the checkboxes in `docs/BLUEPRINT.md`, update `README.md` if the feature set changed, and tell me the truthful resume bullet this week unlocked (from Section 7).

**Week-specific reminders to add to that prompt:**
- **Week 3:** "Uncomment Redis + Postgres in compose; migrate the synchronous API path to an async job queue (RQ or Celery) with idempotent, retryable jobs; add Alembic migrations."
- **Week 4:** "The GitHub App is the headline differentiator — verify webhook signatures, make handlers idempotent, and ensure generated HCL passes `terraform validate` before opening a fix PR."
- **Week 5:** "Add GitHub Actions CI running lint + test + eval, building images, and deploying on merge. Add auth, rate limiting, structured JSON logging, and a metrics endpoint."
- **Week 6:** "Pick ONE stretch feature (anomaly detection, forecast, or live AWS read-only connector), then finalize docs, run the eval, and publish precision/recall + savings-accuracy numbers in the README."

---

## Step 4 — Useful ad-hoc prompts

**When it drifts from the spec:**
> Stop — re-read `docs/BLUEPRINT.md` Section 6. The LLM must not compute or assert any dollar figure. Refactor so all numbers come from the pricing engine and the explainer's output is validated against them.

**When you want an interview-grade decision recorded:**
> Write an ADR in `docs/adr/` explaining why we chose [X] over [alternatives], with the trade-offs, matching the reasoning style in Section 5.

**To generate the issues/board:**
> From `docs/BLUEPRINT.md` Sections 3 and 8, generate a `docs/ISSUES.md` file: one issue per roadmap checkbox with title, the area label, the milestone (M1–M6), and a 2-line description — formatted so I can bulk-create them with the `gh` CLI. Then give me the `gh issue create` command loop.

**Before you show it off:**
> Do a self-review against `docs/BLUEPRINT.md` Section 9 (Interview Prep). For each major feature, confirm the code actually demonstrates the claimed concept, and list anything that would make an interviewer skeptical so I can fix it.

---

## Suggested `LLM.md` (have LLM Code create this in Step 1)

```md
# CloudTrim — Working Conventions

## The one law
The engine is authoritative; the LLM is a narrator. Parsing, detection, pricing,
risk, and remediation are 100% deterministic. The LLM only explains and prioritizes,
and its output is validated against engine numbers (regenerate on mismatch). Never
let the model compute or assert a dollar figure.

## Structure
Monorepo: apps/{api,worker,web}, packages/{engine,ai}, eval/, infra/, docs/.
Business logic lives in packages/engine — the API and worker are thin.

## Conventions
- Python: FastAPI, ruff + black, pytest. Type hints everywhere.
- Every detector: its own file in packages/engine/detectors + a unit test + registry entry.
- Every dollar figure traces to packages/engine/pricing. No magic numbers.
- Commit after each green step; small, reviewable commits.
- New architectural decisions → an ADR in docs/adr/.
- docs/BLUEPRINT.md is the spec. If unsure, re-read the relevant section before coding.

## Definition of done (per feature)
Code + unit tests passing + lint clean + docs/README updated if user-facing +
eval still green.
```

---

### TL;DR
1. `git init` a repo, drop the blueprint in as `docs/BLUEPRINT.md`, start LLM Code inside it.
2. Send the **Bootstrap prompt** → review → commit.
3. Send the **MVP prompt** → review → commit.
4. Each week, send the **per-week driver prompt** with the week number.
5. Always: plan first, tests per feature, small commits, and treat `BLUEPRINT.md` as the contract.
