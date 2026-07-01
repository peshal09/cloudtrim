"""SQL-backed analysis store (BLUEPRINT.md §3 Week 3).

Same interface as the in-memory AnalysisStore (save/get/get_finding/clear) plus
`trend`. save() is idempotent: re-saving an analysis id replaces its rows, so a
retried worker job converges rather than duplicating.
"""

from __future__ import annotations

from engine.aggregate import AnalysisAggregate
from engine.models import Analysis, AnalysisStatus, Finding, Resource
from engine.pipeline import AnalysisResult
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import sessionmaker

from api.db.models import AnalysisRow, Base, FindingRow, ResourceRow


class SqlAnalysisRepository:
    def __init__(self, engine: Engine, create: bool = True) -> None:
        self._engine = engine
        self._Session = sessionmaker(engine, expire_on_commit=False)
        if create:  # dev/test convenience; production migrations are Alembic's job
            Base.metadata.create_all(engine)

    def save(self, result: AnalysisResult) -> None:
        aid = result.analysis.id
        with self._Session.begin() as s:
            s.execute(delete(FindingRow).where(FindingRow.analysis_id == aid))
            s.execute(delete(ResourceRow).where(ResourceRow.analysis_id == aid))
            s.merge(_analysis_row(result))
            for r in result.resources:
                s.add(_resource_row(r, aid))
            for f in result.findings:
                s.add(_finding_row(f, aid))

    def get(self, analysis_id: str) -> AnalysisResult | None:
        with self._Session() as s:
            a = s.get(AnalysisRow, analysis_id)
            if a is None:
                return None
            resources = [
                _to_resource(r)
                for r in s.scalars(
                    select(ResourceRow).where(ResourceRow.analysis_id == analysis_id)
                )
            ]
            findings = [
                _to_finding(f)
                for f in s.scalars(select(FindingRow).where(FindingRow.analysis_id == analysis_id))
            ]
            return AnalysisResult(
                analysis=Analysis(
                    id=a.id,
                    created_at=a.created_at,
                    status=AnalysisStatus(a.status),
                    source_meta=a.source_meta or {},
                    total_monthly_savings=a.total_monthly_savings,
                ),
                resources=resources,
                findings=findings,
                aggregate=AnalysisAggregate.model_validate(a.aggregate),
            )

    def get_finding(self, finding_id: str) -> tuple[Finding, Resource | None] | None:
        with self._Session() as s:
            row = s.scalars(
                select(FindingRow)
                .where(FindingRow.finding_id == finding_id)
                .order_by(FindingRow.pk.desc())  # most recent analysis wins on collision
            ).first()
            if row is None:
                return None
            resource_row = s.get(ResourceRow, row.resource_id)
            resource = _to_resource(resource_row) if resource_row else None
            return _to_finding(row), resource

    def trend(self, limit: int = 100) -> list[dict]:
        with self._Session() as s:
            rows = s.scalars(
                select(AnalysisRow).order_by(AnalysisRow.created_at.asc()).limit(limit)
            )
            return [
                {
                    "id": a.id,
                    "created_at": a.created_at.isoformat(),
                    "total_monthly_savings": a.total_monthly_savings,
                }
                for a in rows
            ]

    def clear(self) -> None:
        with self._Session.begin() as s:
            s.execute(delete(FindingRow))
            s.execute(delete(ResourceRow))
            s.execute(delete(AnalysisRow))


# --- domain <-> row mapping --------------------------------------------------


def _analysis_row(result: AnalysisResult) -> AnalysisRow:
    a = result.analysis
    return AnalysisRow(
        id=a.id,
        created_at=a.created_at,
        status=a.status.value,
        source_meta=a.source_meta,
        total_monthly_savings=a.total_monthly_savings,
        aggregate=result.aggregate.model_dump(),
    )


def _resource_row(r: Resource, aid: str) -> ResourceRow:
    return ResourceRow(
        id=r.id,
        analysis_id=aid,
        identifier=r.identifier,
        type=r.type.value,
        provider=r.provider.value,
        region=r.region,
        instance_type=r.instance_type,
        monthly_cost=r.monthly_cost,
        utilization=r.utilization,
        tags=r.tags,
        raw=r.raw,
    )


def _finding_row(f: Finding, aid: str) -> FindingRow:
    return FindingRow(
        finding_id=f.id,
        analysis_id=aid,
        resource_id=f.resource_id,
        detector=f.detector,
        title=f.title,
        severity=f.severity.value,
        risk=f.risk.value,
        current_cost=f.current_cost,
        projected_cost=f.projected_cost,
        monthly_savings=f.monthly_savings,
        evidence=f.evidence,
        remediation_diff=f.remediation_diff,
        confidence=f.confidence,
        explanation=f.explanation,
        explanation_source=f.explanation_source.value if f.explanation_source else None,
    )


def _to_resource(r: ResourceRow) -> Resource:
    return Resource(
        id=r.id,
        analysis_id=r.analysis_id,
        type=r.type,
        provider=r.provider,
        region=r.region,
        identifier=r.identifier,
        instance_type=r.instance_type,
        monthly_cost=r.monthly_cost,
        utilization=r.utilization,
        tags=r.tags or {},
        raw=r.raw or {},
    )


def _to_finding(f: FindingRow) -> Finding:
    return Finding(
        id=f.finding_id,
        analysis_id=f.analysis_id,
        resource_id=f.resource_id,
        detector=f.detector,
        title=f.title,
        severity=f.severity,
        risk=f.risk,
        current_cost=f.current_cost,
        projected_cost=f.projected_cost,
        monthly_savings=f.monthly_savings,
        evidence=f.evidence or {},
        remediation_diff=f.remediation_diff,
        confidence=f.confidence,
        explanation=f.explanation,
        explanation_source=f.explanation_source,
    )
