"""Deterministic instance-size ladder — used by detectors to propose a rightsizing
target and by the pricing engine to price current vs projected (BLUEPRINT.md §2/§4).

Instance types split into a family and a size, e.g. "t3.large" -> ("t3", "large"),
"db.t3.medium" -> ("db.t3", "medium"). Downsizing steps one rung down the ladder
within the same family.
"""

from __future__ import annotations

# Ordered small -> large. Index is the size rank.
_SIZES: tuple[str, ...] = (
    "nano",
    "micro",
    "small",
    "medium",
    "large",
    "xlarge",
    "2xlarge",
    "4xlarge",
    "8xlarge",
    "12xlarge",
    "16xlarge",
    "24xlarge",
    "32xlarge",
    "48xlarge",
)
_RANK = {size: i for i, size in enumerate(_SIZES)}


def split_type(instance_type: str) -> tuple[str, str] | None:
    """("t3.large") -> ("t3", "large"); returns None if the size isn't recognized."""
    if not instance_type or "." not in instance_type:
        return None
    family, size = instance_type.rsplit(".", 1)
    if size not in _RANK:
        return None
    return family, size


def size_rank(instance_type: str) -> int:
    """Rank of the instance size (bigger = larger); -1 if unrecognized."""
    parts = split_type(instance_type)
    return _RANK[parts[1]] if parts else -1


def downsize(instance_type: str) -> str | None:
    """One rung smaller within the same family, or None if already smallest/unknown."""
    parts = split_type(instance_type)
    if parts is None:
        return None
    family, size = parts
    rank = _RANK[size]
    if rank == 0:
        return None
    return f"{family}.{_SIZES[rank - 1]}"
