"""Analysis endpoints (BLUEPRINT.md §2). Synchronous for the MVP — the engine runs
in-request; Week 3 moves it behind an async job queue.
"""

from __future__ import annotations

from typing import Annotated

from ai import make_explainer
from engine.models import Finding
from engine.pipeline import analyze
from fastapi import APIRouter, File, HTTPException, UploadFile

from api.sample_data import SAMPLE_CSV, SAMPLE_TF
from api.store import store
from api.v1.schemas import AnalysisSummary, FindingDetail

router = APIRouter(tags=["analyses"])

# Template path unless CLOUDTRIM_LLM_API_KEY is set (see [[deterministic-offline-path]]).
_explain = make_explainer()

_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB; tighter limits + streaming come in Week 5


async def _read_text(file: UploadFile) -> str:
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{file.filename} exceeds 5 MB")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{file.filename} is not UTF-8 text") from exc


@router.post("/analyses", status_code=201, response_model=AnalysisSummary)
async def create_analysis(
    terraform: Annotated[UploadFile, File()],
    billing: Annotated[UploadFile | None, File()] = None,
) -> AnalysisSummary:
    tf_text = await _read_text(terraform)
    csv_text = await _read_text(billing) if billing is not None else None

    result = analyze(
        explain=_explain,
        terraform_source=tf_text,
        billing_source=csv_text,
        source_meta={
            "terraform": terraform.filename,
            "billing": billing.filename if billing else None,
        },
    )
    store.save(result)
    return AnalysisSummary.from_result(result)


@router.post("/analyses/sample", status_code=201, response_model=AnalysisSummary)
def create_sample_analysis() -> AnalysisSummary:
    """Instant-demo: run the engine on the bundled sample dataset (no upload)."""
    result = analyze(
        explain=_explain,
        terraform_source=SAMPLE_TF,
        billing_source=SAMPLE_CSV,
        source_meta={"sample": True},
    )
    store.save(result)
    return AnalysisSummary.from_result(result)


@router.get("/analyses/{analysis_id}", response_model=AnalysisSummary)
def get_analysis(analysis_id: str) -> AnalysisSummary:
    result = store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return AnalysisSummary.from_result(result)


@router.get("/analyses/{analysis_id}/findings", response_model=list[Finding])
def list_findings(analysis_id: str) -> list[Finding]:
    result = store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    # Highest-value first: savings desc, then severity.
    return sorted(result.findings, key=lambda f: (-f.monthly_savings, f.severity))


@router.get("/findings/{finding_id}", response_model=FindingDetail)
def get_finding(finding_id: str) -> FindingDetail:
    pair = store.get_finding(finding_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="finding not found")
    finding, resource = pair
    return FindingDetail(finding=finding, resource=resource)
