"""Observability — structured logging, request IDs, metrics, error taxonomy (§3 Week 5).

- JSON logs with a per-request id (propagated via a contextvar and the
  `X-Request-ID` header).
- A hand-rolled Prometheus text exposition at `/metrics` (no extra dependency):
  request counts + duration sums, labelled by the matched route template (low
  cardinality — ids don't explode the label set).
- A consistent error envelope: `{"error": {"type", "message", "request_id"}}`.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("cloudtrim")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = request_id_var.get()
        if rid:
            payload["request_id"] = rid
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


# --- metrics -----------------------------------------------------------------


class Metrics:
    def __init__(self) -> None:
        self._count: dict[tuple[str, str, str], int] = defaultdict(int)
        self._duration: dict[tuple[str, str, str], float] = defaultdict(float)

    def observe(self, method: str, path: str, status: int, seconds: float) -> None:
        key = (method, path, str(status))
        self._count[key] += 1
        self._duration[key] += seconds

    def render(self) -> str:
        lines = ["# TYPE cloudtrim_http_requests_total counter"]
        for (m, p, s), c in sorted(self._count.items()):
            lines.append(
                f'cloudtrim_http_requests_total{{method="{m}",path="{p}",status="{s}"}} {c}'
            )
        lines.append("# TYPE cloudtrim_http_request_duration_seconds_sum counter")
        for (m, p, s), d in sorted(self._duration.items()):
            lines.append(
                f"cloudtrim_http_request_duration_seconds_sum"
                f'{{method="{m}",path="{p}",status="{s}"}} {d:.6f}'
            )
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        self._count.clear()
        self._duration.clear()


metrics = Metrics()


def _llm_metrics() -> str:
    from ai import usage

    return (
        "# TYPE cloudtrim_llm_calls_total counter\n"
        f"cloudtrim_llm_calls_total {usage.calls}\n"
        "# TYPE cloudtrim_llm_input_tokens_total counter\n"
        f"cloudtrim_llm_input_tokens_total {usage.input_tokens}\n"
        "# TYPE cloudtrim_llm_output_tokens_total counter\n"
        f"cloudtrim_llm_output_tokens_total {usage.output_tokens}\n"
        "# TYPE cloudtrim_llm_estimated_cost_usd gauge\n"
        f"cloudtrim_llm_estimated_cost_usd {usage.estimated_cost_usd}\n"
    )


async def metrics_endpoint(_: Request) -> PlainTextResponse:
    return PlainTextResponse(
        metrics.render() + _llm_metrics(), media_type="text/plain; version=0.0.4"
    )


# --- middleware --------------------------------------------------------------


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration = time.perf_counter() - start
            route = request.scope.get("route")
            path = getattr(route, "path", None) or "unmatched"
            metrics.observe(request.method, path, response.status_code, duration)
            response.headers["X-Request-ID"] = rid
            logger.info(
                "request",
                extra={
                    "fields": {
                        "method": request.method,
                        "path": path,
                        "status": response.status_code,
                        "duration_ms": round(duration * 1000, 2),
                    }
                },
            )
            return response
        finally:
            request_id_var.reset(token)


# --- error taxonomy ----------------------------------------------------------

_ERROR_TYPE = {
    400: "invalid_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    413: "payload_too_large",
    429: "rate_limited",
    501: "not_implemented",
    503: "unavailable",
}


def _envelope(status: int, message: str) -> dict:
    return {
        "error": {
            "type": _ERROR_TYPE.get(status, "error"),
            "message": message,
            "request_id": request_id_var.get(),
        },
        "detail": message,  # kept for compatibility with the default FastAPI shape
    }


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_envelope(exc.status_code, exc.detail))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error")
    return JSONResponse(status_code=500, content=_envelope(500, "internal server error"))
