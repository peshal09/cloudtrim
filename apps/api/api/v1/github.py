"""GitHub webhook endpoint (BLUEPRINT.md §3 Week 4).

Verifies the HMAC signature, dedupes redeliveries by X-GitHub-Delivery (idempotency),
and dispatches to the handler. The GitHub client is a dependency so tests can inject a
fake; production resolves it from CLOUDTRIM_GITHUB_TOKEN.
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from api.github.client import GitHubClient, get_github_client
from api.github.handler import handle_event
from api.github.signature import verify_signature
from api.settings import settings

router = APIRouter(tags=["github"])

# Idempotency: delivery ids already processed. In-memory for the MVP; a shared
# Redis/DB set would make this correct across replicas.
_seen_deliveries: set[str] = set()


def get_client() -> GitHubClient:
    client = get_github_client()
    if client is None:
        raise HTTPException(status_code=503, detail="GitHub token not configured")
    return client


@router.post("/github/webhook")
async def github_webhook(
    request: Request,
    client: Annotated[GitHubClient, Depends(get_client)],
) -> dict:
    body = await request.body()
    if not verify_signature(
        settings.github_webhook_secret, body, request.headers.get("X-Hub-Signature-256")
    ):
        raise HTTPException(status_code=401, detail="invalid signature")

    delivery = request.headers.get("X-GitHub-Delivery", "")
    if delivery and delivery in _seen_deliveries:
        return {"status": "duplicate"}
    if delivery:
        _seen_deliveries.add(delivery)

    event = request.headers.get("X-GitHub-Event", "")
    return handle_event(event, json.loads(body), client)
