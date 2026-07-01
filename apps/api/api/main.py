from fastapi import FastAPI

from api.settings import settings
from api.v1.router import router as v1_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
