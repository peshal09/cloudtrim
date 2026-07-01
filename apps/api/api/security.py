"""API-key auth + rate limiting (BLUEPRINT.md §3 Week 5).

Both are opt-in so the zero-config demo and tests stay open:
- auth is enforced only when CLOUDTRIM_API_KEYS is set (Bearer token or X-API-Key);
- rate limiting only when CLOUDTRIM_RATE_LIMIT_PER_MINUTE > 0.

The limiter is a per-client fixed window, in-memory (note: a shared Redis counter
would make it correct across replicas).
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from api.settings import settings


def _extract_key(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer ") :]
    return request.headers.get("X-API-Key")


async def require_api_key(request: Request) -> None:
    keys = settings.api_key_set()
    if not keys:  # open mode
        return
    key = _extract_key(request)
    if not key or key not in keys:
        raise HTTPException(status_code=401, detail="missing or invalid API key")
    request.state.api_key = key


# client -> (window_minute, count)
_windows: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))


async def rate_limit(request: Request) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    client = getattr(request.state, "api_key", None) or (
        request.client.host if request.client else "anon"
    )
    minute = int(time.time() // 60)
    window, count = _windows[client]
    count = count + 1 if window == minute else 1
    _windows[client] = (minute, count)
    if count > limit:
        raise HTTPException(status_code=429, detail="rate limit exceeded")


def reset_rate_limit() -> None:
    _windows.clear()
