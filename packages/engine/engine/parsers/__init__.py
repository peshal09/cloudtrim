"""Source-specific parsers → normalized `Resource` list.

Deterministic and dependency-light: Terraform (HCL or `terraform show -json`) and
billing CSV. Merging config + billing into one model is the normalizer's job (§4).
"""

from engine.parsers.billing import parse_billing
from engine.parsers.k8s import parse_k8s
from engine.parsers.terraform import parse_terraform

__all__ = ["parse_terraform", "parse_billing", "parse_k8s"]
