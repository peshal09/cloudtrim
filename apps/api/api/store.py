"""Analysis store — in-memory by default, SQL-backed when CLOUDTRIM_DATABASE_URL is
set (BLUEPRINT.md §3 Week 3).

The in-memory store keeps the zero-dependency demo working; the SQL repository
(api.db.repository) provides persistence for the async worker path. Both expose the
same interface (save/get/get_finding/trend/clear).
"""

from __future__ import annotations

from engine.models import Finding, Resource
from engine.pipeline import AnalysisResult

from api.settings import settings


class AnalysisStore:
    def __init__(self) -> None:
        self._analyses: dict[str, AnalysisResult] = {}
        self._finding_to_analysis: dict[str, str] = {}

    def save(self, result: AnalysisResult) -> None:
        self._analyses[result.analysis.id] = result
        for finding in result.findings:
            self._finding_to_analysis[finding.id] = result.analysis.id

    def get(self, analysis_id: str) -> AnalysisResult | None:
        return self._analyses.get(analysis_id)

    def get_finding(self, finding_id: str) -> tuple[Finding, Resource | None] | None:
        analysis_id = self._finding_to_analysis.get(finding_id)
        if analysis_id is None:
            return None
        result = self._analyses[analysis_id]
        finding = next((f for f in result.findings if f.id == finding_id), None)
        if finding is None:
            return None
        resource = next((r for r in result.resources if r.id == finding.resource_id), None)
        return finding, resource

    def trend(self, limit: int = 100) -> list[dict]:
        results = sorted(self._analyses.values(), key=lambda r: r.analysis.created_at)[:limit]
        return [
            {
                "id": r.analysis.id,
                "created_at": r.analysis.created_at.isoformat(),
                "total_monthly_savings": r.analysis.total_monthly_savings,
            }
            for r in results
        ]

    def clear(self) -> None:
        self._analyses.clear()
        self._finding_to_analysis.clear()


def make_store():
    """Return the configured store: SQL-backed if a database is set, else in-memory."""
    if settings.database_url:
        from api.db.repository import SqlAnalysisRepository
        from api.db.session import make_engine

        return SqlAnalysisRepository(make_engine(settings.database_url))
    return AnalysisStore()


# Process-wide store, resolved once from settings.
store = make_store()
