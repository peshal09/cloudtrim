"""Core domain models for the CloudTrim engine (BLUEPRINT.md §2 data model).

These are deterministic value objects shared across parsers, detectors, pricing,
risk, and the AI layer. No LLM or I/O lives here. Monetary values are USD/month
floats for the MVP; a future move to Decimal would live behind the pricing engine.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Provider(StrEnum):
    AWS = "aws"


class ResourceType(StrEnum):
    """Normalized resource type. `raw` retains the source-specific type string."""

    EC2 = "ec2"
    RDS = "rds"
    S3 = "s3"
    EBS = "ebs"
    OTHER = "other"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Risk(StrEnum):
    """Deterministic rollout risk of applying a finding's remediation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ExplanationSource(StrEnum):
    """Which path produced a finding's explanation. Emitted for UI + CI assertions."""

    TEMPLATE = "template"
    LLM = "llm"


class Resource(BaseModel):
    """A cloud resource, normalized from IaC config and/or billing data."""

    id: str = Field(default_factory=_new_id)
    analysis_id: str | None = None
    type: ResourceType = ResourceType.OTHER
    provider: Provider = Provider.AWS
    region: str | None = None
    identifier: str  # join key: TF address, resource name, or billing resource id
    instance_type: str | None = None  # e.g. "t3.large", "db.t3.medium"
    monthly_cost: float | None = None  # from billing; None if config-only
    utilization: float | None = None  # primary signal, e.g. avg CPU %  (0..100)
    tags: dict[str, str] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)  # source-specific untouched data


class Finding(BaseModel):
    """A detected waste/anti-pattern on a resource, priced and risk-scored.

    Every dollar figure is set by the deterministic engine (pricing). The
    `explanation`/`explanation_source` fields are populated last by the AI layer,
    whose output is validated against `monthly_savings` regardless of source.
    """

    id: str = Field(default_factory=_new_id)
    analysis_id: str | None = None
    resource_id: str
    detector: str  # detector key, e.g. "idle_ec2"
    title: str
    severity: Severity
    risk: Risk = Risk.MEDIUM  # provisional; set by the deterministic risk scorer (§ step 6)
    current_cost: float = 0.0  # USD/month, from pricing engine
    projected_cost: float = 0.0  # USD/month after remediation
    monthly_savings: float = 0.0  # current_cost - projected_cost
    evidence: dict[str, Any] = Field(default_factory=dict)  # structured, drives explanation
    remediation_diff: str | None = None  # HCL/YAML change (codegen; Week 4 deepens)
    confidence: float = 1.0  # detector confidence 0..1
    explanation: str | None = None
    explanation_source: ExplanationSource | None = None


class Analysis(BaseModel):
    """One upload → analysis run and its aggregate summary."""

    id: str = Field(default_factory=_new_id)
    created_at: datetime = Field(default_factory=_utcnow)
    status: AnalysisStatus = AnalysisStatus.PENDING
    source_meta: dict[str, Any] = Field(default_factory=dict)  # filenames, sizes, counts
    total_monthly_savings: float = 0.0

    def severity_counts(self, findings: list[Finding]) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for f in findings:
            counts[f.severity.value] += 1
        return counts


__all__ = [
    "Provider",
    "ResourceType",
    "Severity",
    "Risk",
    "AnalysisStatus",
    "ExplanationSource",
    "Resource",
    "Finding",
    "Analysis",
]
