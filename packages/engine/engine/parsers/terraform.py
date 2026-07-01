"""Terraform parser → normalized `Resource` list.

Two input modes (BLUEPRINT.md §5): a `terraform show -json` plan/state document
(primary, accurate/resolved) and raw HCL `.tf` (fallback, via python-hcl2). Both
produce config-side resources — cost/utilization come from billing + the normalizer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import hcl2

from engine.models import Resource, ResourceType

# TF resource type -> (normalized type, attribute holding the instance size)
_TF_TYPE_MAP: dict[str, tuple[ResourceType, str | None]] = {
    "aws_instance": (ResourceType.EC2, "instance_type"),
    "aws_db_instance": (ResourceType.RDS, "instance_class"),
    "aws_s3_bucket": (ResourceType.S3, None),
    "aws_ebs_volume": (ResourceType.EBS, None),
}


def parse_terraform(source: str | Path) -> list[Resource]:
    """Parse a Terraform document (plan JSON or HCL) into config-side resources."""
    text = Path(source).read_text() if _looks_like_path(source) else str(source)
    plan = _try_json_plan(text)
    return _parse_plan(plan) if plan is not None else _parse_hcl(text)


# --- plan / state JSON -------------------------------------------------------


def _try_json_plan(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict) and any(
        k in data for k in ("planned_values", "values", "resource_changes")
    ):
        return data
    return None


def _parse_plan(plan: dict[str, Any]) -> list[Resource]:
    root = plan.get("planned_values", plan.get("values", {})).get("root_module", {})
    resources: list[Resource] = []

    def walk(module: dict[str, Any]) -> None:
        for r in module.get("resources", []):
            res = _resource_from_plan(r)
            if res is not None:
                resources.append(res)
        for child in module.get("child_modules", []):
            walk(child)

    walk(root)
    return resources


def _resource_from_plan(r: dict[str, Any]) -> Resource | None:
    tf_type = r.get("type", "")
    kind, size_attr = _TF_TYPE_MAP.get(tf_type, (ResourceType.OTHER, None))
    values: dict[str, Any] = r.get("values", {}) or {}
    return Resource(
        type=kind,
        identifier=r.get("address") or f"{tf_type}.{r.get('name', '')}",
        region=values.get("region"),
        instance_type=values.get(size_attr) if size_attr else None,
        tags={str(k): str(v) for k, v in (values.get("tags") or {}).items()},
        raw={"tf_type": tf_type, "values": values},
    )


# --- raw HCL -----------------------------------------------------------------


def _parse_hcl(text: str) -> list[Resource]:
    data = hcl2.loads(text)
    resources: list[Resource] = []
    for block in data.get("resource", []):
        for tf_type_key, bodies in block.items():
            tf_type = _unquote(tf_type_key)
            kind, size_attr = _TF_TYPE_MAP.get(tf_type, (ResourceType.OTHER, None))
            for name_key, raw_attrs in bodies.items():
                name = _unquote(name_key)
                attrs = {k: _clean(v) for k, v in raw_attrs.items() if k != "__is_block__"}
                tags = attrs.get("tags") if isinstance(attrs.get("tags"), dict) else {}
                resources.append(
                    Resource(
                        type=kind,
                        identifier=f"{tf_type}.{name}",
                        region=attrs.get("region"),
                        instance_type=attrs.get(size_attr) if size_attr else None,
                        tags={str(k): str(v) for k, v in tags.items()},
                        raw={"tf_type": tf_type, "attrs": attrs},
                    )
                )
    return resources


# --- helpers -----------------------------------------------------------------


def _looks_like_path(source: str | Path) -> bool:
    if isinstance(source, Path):
        return True
    # A short single-line string that exists on disk is a path; HCL/JSON bodies are not.
    return "\n" not in source and len(source) < 4096 and Path(source).exists()


def _unquote(s: Any) -> Any:
    """python-hcl2 (v8) wraps keys and string literals in literal double quotes."""
    if isinstance(s, str) and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return _unquote(value)
    if isinstance(value, dict):
        return {_unquote(k): _clean(v) for k, v in value.items() if k != "__is_block__"}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value
