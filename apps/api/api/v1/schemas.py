"""API response models (BLUEPRINT.md §2)."""

from __future__ import annotations

from datetime import datetime

from engine.models import AnalysisStatus, Finding, Resource
from engine.pipeline import AnalysisResult
from pydantic import BaseModel


class AnalysisSummary(BaseModel):
    id: str
    status: AnalysisStatus
    created_at: datetime
    total_monthly_savings: float
    findings_count: int
    severity_counts: dict[str, int]
    source_meta: dict

    @classmethod
    def from_result(cls, result: AnalysisResult) -> AnalysisSummary:
        a = result.analysis
        return cls(
            id=a.id,
            status=a.status,
            created_at=a.created_at,
            total_monthly_savings=a.total_monthly_savings,
            findings_count=len(result.findings),
            severity_counts=a.severity_counts(result.findings),
            source_meta=a.source_meta,
        )


class FindingDetail(BaseModel):
    finding: Finding
    resource: Resource | None
