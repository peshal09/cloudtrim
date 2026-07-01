"""Async job queue (RQ) — enqueue side (BLUEPRINT.md §3 Week 3).

Async mode is enabled only when both a Redis URL and a database are configured;
otherwise the API runs the analysis synchronously against the in-memory store. The
job is referenced by string path so the API image needn't import the worker package.
"""

from __future__ import annotations

from typing import Any

from api.settings import settings

_JOB = "worker.jobs.run_analysis_job"


def async_enabled() -> bool:
    return bool(settings.redis_url and settings.database_url)


def get_queue(connection: Any = None, is_async: bool = True) -> Any:
    from redis import Redis
    from rq import Queue

    conn = connection or Redis.from_url(settings.redis_url)
    return Queue("cloudtrim", connection=conn, is_async=is_async)


def enqueue_analysis(
    queue: Any,
    analysis_id: str,
    terraform: str | None,
    billing: str | None,
    kubernetes: str | None,
    source_meta: dict | None = None,
) -> Any:
    from rq import Retry

    return queue.enqueue(
        _JOB,
        analysis_id,
        terraform,
        billing,
        kubernetes,
        source_meta or {},
        retry=Retry(max=2),  # idempotent job -> safe to retry
        job_timeout=600,
    )
