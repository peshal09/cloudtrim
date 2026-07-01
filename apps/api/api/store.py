"""In-memory analysis store (MVP). Postgres + persistence arrive in Week 3 (§3).

Holds completed AnalysisResults keyed by analysis id, plus a finding-id index so a
single finding is retrievable without knowing its analysis.
"""

from __future__ import annotations

from engine.models import Finding, Resource
from engine.pipeline import AnalysisResult


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

    def clear(self) -> None:
        self._analyses.clear()
        self._finding_to_analysis.clear()


# Process-wide singleton for the MVP (swapped for a DB-backed store in Week 3).
store = AnalysisStore()
