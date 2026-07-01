# ADR 0002 — Pricing via a committed snapshot + Price List Query API

- **Status:** Accepted
- **Date:** 2026-06-30
- **Reference:** BLUEPRINT.md §5 (Technology Choices), §6 (AI Architecture); builds on [ADR-0001](0001-deterministic-core-llm-explains.md)

## Context

The pricing engine is the single source of truth for every dollar figure (ADR-0001).
How it obtains AWS prices has to satisfy three constraints at once:

1. **Determinism.** The eval harness reports savings-accuracy and precision/recall as
   headline credibility numbers. If prices are fetched live, those numbers drift every
   run and tests turn flaky.
2. **Zero-friction demo.** The demo must run instantly, offline, with no AWS account —
   including in an interview or in CI.
3. **Small repo.** No multi-GB blobs in git.

There are two AWS pricing surfaces, and conflating them is the trap:
- **Offer File API** — the bulk `index.json` per service. Multi-GB. Impractical to
  download or commit. *Not used.*
- **Price List Query API** — `pricing:GetProducts` with filters (service + instance
  type + region). Returns only the SKUs asked for — kilobytes. This is the right tool
  for live lookups; live fetch was never the multi-GB problem.

## Decision

A **three-tier lookup** behind `PricingClient.get_price(instance_type, region)`:

1. **Committed `snapshot.json`** (tier 1) — a small, curated set of on-demand hourly
   prices for the instance types our fixtures use. This is the **only tier tests and
   the eval harness touch**, which pins their numbers run-to-run.
2. **On-disk cache** (tier 2) — `~/.cloudtrim/pricing_cache/prices.json`, populated by
   tier 3. Best-effort; a write failure never fails a lookup.
3. **Live Price List Query API** (tier 3) — `boto3` `get_products`, used only when
   `allow_live` is set and creds/boto3 are present. Result is cached to tier 2.

`scripts/build_pricing_snapshot.py` regenerates tier 1 from the Query API at build
time (run manually with creds); its output is committed.

**Caveat baked into the client:** the Query API is only served from `us-east-1` /
`ap-south-1`, so the client pins the *API call* region there regardless of the region
being priced.

## Consequences

**Positive**
- Tests, eval, and the demo are deterministic and offline — no creds, no network.
- Honest "live pricing" story preserved: real prices flow in via the Query API and are
  cached; the snapshot is a pinned baseline, not a fake.
- Repo stays KB-sized; the bulk Offer File is never involved.

**Negative / trade-offs**
- The snapshot must be regenerated to stay current (a manual build step) and to cover
  new instance types.
- Snapshot list prices can diverge from a specific account's negotiated/actual billed
  cost. For deletions with no priced type we fall back to the observed billing cost;
  otherwise savings are list-price based (documented in `savings.py`).

**Neutral**
- Adds `boto3` as a dependency, exercised only by tier 3 and the build script.
