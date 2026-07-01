"""SQLAlchemy ORM: Analyses / Resources / Findings (BLUEPRINT.md §3 Week 3).

JSON columns (portable across Postgres and the SQLite test tier) hold the
heterogeneous bits — source_meta, the aggregate, resource `raw`, and finding
`evidence`. Postgres would use JSONB in production; JSON keeps the tests offline.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AnalysisRow(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String)
    source_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    total_monthly_savings: Mapped[float] = mapped_column(Float, default=0.0)
    aggregate: Mapped[dict] = mapped_column(JSON, default=dict)


class ResourceRow(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # uuid, globally unique
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    identifier: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String, nullable=True)
    instance_type: Mapped[str | None] = mapped_column(String, nullable=True)
    monthly_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    utilization: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)


class FindingRow(Base):
    __tablename__ = "findings"

    # Surrogate PK: the domain finding id (detector:identifier) is unique within an
    # analysis but repeats across analyses, so it can't be the primary key.
    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String, index=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    resource_id: Mapped[str] = mapped_column(String)
    detector: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    risk: Mapped[str] = mapped_column(String)
    current_cost: Mapped[float] = mapped_column(Float, default=0.0)
    projected_cost: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_savings: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    remediation_diff: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    explanation: Mapped[str | None] = mapped_column(String, nullable=True)
    explanation_source: Mapped[str | None] = mapped_column(String, nullable=True)
