"""Remediation codegen — turn a finding into an applicable patch (BLUEPRINT.md §3 Week 4).

Deterministic: given a finding and the original source text, emit a unified diff that
rightsizes the resource (Terraform) or tunes the workload (Kubernetes). The patch is
validated by re-parsing the patched text; the GitHub flow additionally runs
`terraform validate` when the binary is available.
"""

from engine.remediation.hcl_codegen import generate_tf_patch, rewrite_tf
from engine.remediation.validate import (
    terraform_validate,
    validate_hcl,
    validate_yaml,
)
from engine.remediation.yaml_patch import generate_k8s_patch, rewrite_k8s

__all__ = [
    "generate_tf_patch",
    "rewrite_tf",
    "generate_k8s_patch",
    "rewrite_k8s",
    "validate_hcl",
    "validate_yaml",
    "terraform_validate",
]
