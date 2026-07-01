"""Response cache keyed on a finding's content hash (BLUEPRINT.md §6).

In-memory for the MVP; a Redis-backed cache lands in Week 5. Keying on the engine
numbers + model means the cache invalidates when a figure or the model changes.
"""

from __future__ import annotations

import hashlib
import json

from engine.models import Finding


def finding_key(finding: Finding, model: str) -> str:
    payload = {
        "id": finding.id,
        "current": round(finding.current_cost, 2),
        "projected": round(finding.projected_cost, 2),
        "savings": round(finding.monthly_savings, 2),
        "risk": finding.risk.value,
        "model": model,
    }
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


class ExplanationCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[str, str]] = {}

    def get(self, key: str) -> tuple[str, str] | None:
        return self._store.get(key)

    def set(self, key: str, value: tuple[str, str]) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()


cache = ExplanationCache()
