"""Validate generated remediations (BLUEPRINT.md §3 Week 4).

Deterministic tier: re-parse the patched text (hcl2 / PyYAML) to confirm it's still
structurally valid. Prod tier: if the `terraform` binary is present, run
`terraform validate` for a stronger guarantee before opening a fix PR.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import hcl2
import yaml


def validate_hcl(text: str) -> bool:
    try:
        hcl2.loads(text)
        return True
    except Exception:  # noqa: BLE001 — any parse failure means invalid
        return False


def validate_yaml(text: str) -> bool:
    try:
        list(yaml.safe_load_all(text))
        return True
    except yaml.YAMLError:
        return False


def terraform_available() -> bool:
    return shutil.which("terraform") is not None


def terraform_validate(text: str) -> bool:
    """Run `terraform validate` on the text. Returns True if the binary is absent
    (deterministic re-parse is the fallback gate) or validation passes."""
    if not terraform_available():
        return validate_hcl(text)
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.tf").write_text(text)
        init = subprocess.run(["terraform", "init", "-backend=false"], cwd=tmp, capture_output=True)
        if init.returncode != 0:
            return False
        result = subprocess.run(["terraform", "validate"], cwd=tmp, capture_output=True)
        return result.returncode == 0
