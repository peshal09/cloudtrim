from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.observability import (
    ObservabilityMiddleware,
    configure_logging,
    http_exception_handler,
    metrics_endpoint,
    unhandled_exception_handler,
)
from api.settings import settings
from api.v1.router import router as v1_router


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_route("/metrics", metrics_endpoint)  # unversioned, unauthenticated
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
