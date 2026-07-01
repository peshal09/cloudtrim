"""Response cache keyed on a finding's content hash, with TTLs (§3 Week 5/6).

In-memory for the MVP; a Redis-backed cache lands in production. Keying on the
engine numbers + model means the cache invalidates when a figure or the model
changes. Entries expire after CLOUDTRIM_CACHE_TTL_SECONDS (0 disables expiry).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable

from engine.models import Finding

_DEFAULT_TTL = float(os.getenv("CLOUDTRIM_CACHE_TTL_SECONDS", "3600"))


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
    def __init__(self, ttl: float | None = None, clock: Callable[[], float] = time.time) -> None:
        self._ttl = _DEFAULT_TTL if ttl is None else ttl
        self._clock = clock
        self._store: dict[str, tuple[tuple[str, str], float | None]] = {}

    def get(self, key: str) -> tuple[str, str] | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expiry = item
        if expiry is not None and self._clock() >= expiry:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: tuple[str, str]) -> None:
        expiry = self._clock() + self._ttl if self._ttl > 0 else None
        self._store[key] = (value, expiry)

    def clear(self) -> None:
        self._store.clear()


cache = ExplanationCache()
