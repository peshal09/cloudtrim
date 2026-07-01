"""Seed the demo analysis into the configured store (BLUEPRINT.md §3 Week 3).

Runs the bundled sample dataset through the engine and persists it. With
CLOUDTRIM_DATABASE_URL set this seeds Postgres; otherwise it's a no-op in-memory.

    docker compose run --rm api python scripts/seed_demo.py
    # or locally:  CLOUDTRIM_DATABASE_URL=... make seed
"""

from __future__ import annotations

from ai import make_explainer
from api.sample_data import SAMPLE_CSV, SAMPLE_K8S, SAMPLE_TF
from api.store import make_store
from engine.pipeline import analyze


def main() -> int:
    result = analyze(
        terraform_source=SAMPLE_TF,
        billing_source=SAMPLE_CSV,
        kubernetes_source=SAMPLE_K8S,
        explain=make_explainer(),
        source_meta={"sample": True, "seed": True},
    )
    make_store().save(result)
    print(
        f"seeded analysis {result.analysis.id}: "
        f"{len(result.findings)} findings, "
        f"${result.analysis.total_monthly_savings}/mo"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
