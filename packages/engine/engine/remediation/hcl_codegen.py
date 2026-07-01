"""Terraform remediation codegen (BLUEPRINT.md §3 Week 4).

`rewrite_tf` returns the corrected file content (what a bot commits); `tf_patch`
returns a unified diff (what the UI shows). Both locate the resource block in a
brace-depth-aware way so nested `tags {}` blocks don't confuse the scan, then rewrite
the instance type on the exact line. Only rightsize findings are patchable; others
return None. Input must be HCL text (not `terraform show -json`).
"""

from __future__ import annotations

import difflib
import re

from engine.models import Finding

# detector -> the HCL attribute carrying the instance size
_ATTR = {
    "idle_ec2": "instance_type",
    "oversized_ec2": "instance_type",
    "overprovisioned_rds": "instance_class",
}


def rewrite_tf(finding: Finding, source_text: str) -> str | None:
    """Corrected `.tf` content with the instance type rightsized, or None."""
    ev = finding.evidence
    if ev.get("action") != "rightsize":
        return None
    current = ev.get("current_instance_type")
    target = ev.get("target_instance_type")
    attr = _ATTR.get(finding.detector)
    if not (current and target and attr):
        return None

    # finding.id is "detector:<tf address>", e.g. "idle_ec2:aws_instance.web".
    comps = finding.id.split(":", 1)[1].split(".")
    if len(comps) < 2:
        return None
    tf_type, name = comps[-2], comps[-1]

    lines = source_text.splitlines()
    header = re.compile(rf'resource\s+"{re.escape(tf_type)}"\s+"{re.escape(name)}"\s*\{{')
    start = next((i for i, ln in enumerate(lines) if header.search(ln)), None)
    if start is None:
        return None

    depth = 0
    end = len(lines) - 1
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0:
            end = i
            break

    attr_re = re.compile(rf'({attr}\s*=\s*"){re.escape(current)}(")')
    patched = lines[:]
    for i in range(start, end + 1):
        new = attr_re.sub(rf"\g<1>{target}\g<2>", lines[i], count=1)
        if new != lines[i]:
            patched[i] = new
            break
    else:
        return None  # attribute line not found

    trailing = "\n" if source_text.endswith("\n") else ""
    return "\n".join(patched) + trailing


def generate_tf_patch(finding: Finding, source_text: str) -> str | None:
    """Unified diff of the rightsize change, or None."""
    patched = rewrite_tf(finding, source_text)
    if patched is None:
        return None
    label = finding.id.split(":", 1)[1].replace(".", "_") + ".tf"
    diff = difflib.unified_diff(
        source_text.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
    )
    return "".join(diff)
