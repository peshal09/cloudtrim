from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


# Feature endpoints (analyses, findings) are added in Week 1 MVP — see docs/BLUEPRINT.md §2.
