from fastapi import APIRouter

from api.v1.analyses import router as analyses_router
from api.v1.github import router as github_router

router = APIRouter()


@router.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


router.include_router(analyses_router)
router.include_router(github_router)
