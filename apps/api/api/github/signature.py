"""GitHub webhook signature verification (BLUEPRINT.md §3 Week 4).

HMAC-SHA256 over the raw request body, constant-time compared against the
`X-Hub-Signature-256` header. Verifying the signature is what makes the webhook
endpoint safe to expose publicly.
"""

from __future__ import annotations

import hashlib
import hmac


def verify_signature(secret: str | None, body: bytes, header: str | None) -> bool:
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
