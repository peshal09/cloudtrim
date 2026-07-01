"""Worker job: run one analysis and persist it (BLUEPRINT.md §3 Week 3).

Idempotent + retryable: keyed on the pre-assigned analysis_id, and the repository's
save() replaces that analysis's rows — so a retry converges instead of duplicating.
Persists to the same store the API reads from (Postgres, via CLOUDTRIM_DATABASE_URL).
"""

from __future__ import annotations

from ai import make_explainer
from engine.pipeline import analyze


def run_analysis_job(
    analysis_id: str,
    terraform: str | None,
    billing: str | None,
    kubernetes: str | None,
    source_meta: dict | None = None,
) -> str:
    from api.store import make_store  # shared persistence (same DB as the API)

    result = analyze(
        analysis_id=analysis_id,
        terraform_source=terraform,
        billing_source=billing,
        kubernetes_source=kubernetes,
        explain=make_explainer(),
        source_meta=source_meta or {},
    )
    make_store().save(result)
    return analysis_id
