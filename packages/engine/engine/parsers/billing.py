"""Billing/utilization CSV parser → cost-side `Resource` list.

A simplified per-resource monthly CSV (not full AWS CUR — that's a later concern).
Column names are matched case-insensitively with common aliases so real exports
drop in with minimal massaging. Cost/utilization here enrich config-side resources
during normalization (§4).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from engine.models import Provider, Resource, ResourceType

# canonical field -> accepted header aliases (lowercased)
_ALIASES: dict[str, tuple[str, ...]] = {
    "identifier": ("identifier", "resource_id", "resource", "address", "arn"),
    "type": ("type", "service", "resource_type"),
    "region": ("region", "aws_region", "location"),
    "instance_type": ("instance_type", "instance_class", "size"),
    "monthly_cost": ("monthly_cost", "cost", "cost_usd", "unblended_cost", "amount"),
    "utilization": ("utilization", "cpu", "cpu_utilization", "avg_cpu", "cpu_pct"),
    "tags": ("tags",),
}

_TYPE_KEYWORDS: tuple[tuple[str, ResourceType], ...] = (
    ("ec2", ResourceType.EC2),
    ("instance", ResourceType.EC2),
    ("rds", ResourceType.RDS),
    ("db", ResourceType.RDS),
    ("s3", ResourceType.S3),
    ("ebs", ResourceType.EBS),
    ("volume", ResourceType.EBS),
)


def parse_billing(source: str | Path) -> list[Resource]:
    text = Path(source).read_text() if _looks_like_path(source) else str(source)
    reader = csv.DictReader(io.StringIO(text))
    resources: list[Resource] = []
    for row in reader:
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        identifier = _pick(norm, "identifier")
        if not identifier:
            continue  # a row we can't join on is useless
        resources.append(
            Resource(
                type=_map_type(_pick(norm, "type")),
                provider=Provider.AWS,
                identifier=identifier,
                region=_pick(norm, "region") or None,
                instance_type=_pick(norm, "instance_type") or None,
                monthly_cost=_to_float(_pick(norm, "monthly_cost")),
                utilization=_to_float(_pick(norm, "utilization")),
                tags=_parse_tags(_pick(norm, "tags")),
                raw={"billing_row": norm},
            )
        )
    return resources


def _pick(row: dict[str, str], field: str) -> str:
    for alias in _ALIASES[field]:
        if row.get(alias):
            return row[alias]
    return ""


def _map_type(value: str) -> ResourceType:
    v = value.lower()
    try:
        return ResourceType(v)  # exact "ec2"/"rds"/"s3"/"ebs"
    except ValueError:
        pass
    for keyword, kind in _TYPE_KEYWORDS:
        if keyword in v:
            return kind
    return ResourceType.OTHER


def _to_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace("$", "").replace(",", "").rstrip("%"))
    except ValueError:
        return None


def _parse_tags(value: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for pair in value.split(";"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            tags[k.strip()] = v.strip()
    return tags


def _looks_like_path(source: str | Path) -> bool:
    if isinstance(source, Path):
        return True
    return "\n" not in source and len(source) < 4096 and Path(source).exists()
