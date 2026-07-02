# ADR 0001 — Deterministic core, LLM explains, output validated

- **Status:** Accepted
- **Date:** 2026-06-30
- **Context section reference:** BLUEPRINT.md §6 (AI Architecture)

## Context

CloudTrim's value depends on its numbers being trustworthy. Cost findings and
savings estimates drive real infrastructure changes and, eventually, auto-generated
fix PRs. An LLM that computes or asserts dollar figures can hallucinate — a single
wrong savings number destroys the product's credibility and its core interview
talking point.

At the same time, the LLM is genuinely valuable for what deterministic code is bad
at: architect-grade explanation, prioritization, and prose (PR descriptions, Q&A).

## Decision

Draw a hard architectural boundary:

- **The engine is authoritative.** Parsing, normalization, cross-signal joins,
  detection rules, pricing/savings math, risk scoring, and remediation codegen are
  100% deterministic and live in `packages/engine`. If the LLM disappeared,
  CloudTrim would still produce correct findings and correct dollar figures.
- **The LLM is a narrator.** It only explains and prioritizes, grounded on the
  finding's structured evidence. It never computes or asserts a number.
- **Outputs are validated.** The AI layer parses any dollar figure the model cites
  and rejects/regenerates the explanation if it doesn't match the engine's value.
  Structured output, retry/fallback, and response caching back this up.

## Consequences

**Positive**
- No hallucinated savings numbers reach the user — the trust story is enforced in code.
- The engine is independently testable (unit tests + eval harness precision/recall)
  without any LLM in the loop.
- Clear separation of concerns: `packages/engine` (deterministic) vs `packages/ai`
  (bounded narration).

**Negative / trade-offs**
- Extra work: a validation + regeneration step and a strict output schema.
- The LLM cannot "fix up" a finding — if the engine is wrong, the explanation is
  wrong; correctness pressure stays on the deterministic code (this is intentional).

**Neutral**
- Every dollar figure must trace to `packages/engine/engine/pricing`; no magic
  numbers elsewhere. Enforced by convention and review (see `CONVENTIONS.md`).
