"""Kubernetes remediation codegen (BLUEPRINT.md §3 Week 4).

Basic, applicable YAML patches. Currently: replica over-provisioning -> reduce the
replica count (the fuller fix is adding an HPA, noted in the finding). Scoped to the
named workload so the right `replicas:` line is edited in a multi-document manifest.
"""

from __future__ import annotations

import difflib
import re

from engine.models import Finding

_RECOMMENDED_REPLICAS = 3


def rewrite_k8s(finding: Finding, source_text: str) -> str | None:
    """Corrected manifest content, or None."""
    if finding.detector != "k8s_replica_overprovisioned":
        return None
    current = finding.evidence.get("replicas")
    if not isinstance(current, int) or current <= _RECOMMENDED_REPLICAS:
        return None
    name = finding.id.split(":", 1)[1].split("/")[-1]

    lines = source_text.splitlines()
    name_re = re.compile(rf"^\s*name:\s*{re.escape(name)}\s*$")
    replica_re = re.compile(rf"^(\s*replicas:\s*){current}\s*$")

    name_idx = next((i for i, ln in enumerate(lines) if name_re.match(ln)), None)
    if name_idx is None:
        return None

    patched = lines[:]
    for i in range(name_idx, min(len(lines), name_idx + 20)):
        m = replica_re.match(lines[i])
        if m:
            patched[i] = f"{m.group(1)}{_RECOMMENDED_REPLICAS}"
            break
    else:
        return None

    trailing = "\n" if source_text.endswith("\n") else ""
    return "\n".join(patched) + trailing


def generate_k8s_patch(finding: Finding, source_text: str) -> str | None:
    patched = rewrite_k8s(finding, source_text)
    if patched is None:
        return None
    label = finding.id.split(":", 1)[1].replace("/", "_") + ".yaml"
    diff = difflib.unified_diff(
        source_text.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
    )
    return "".join(diff)
