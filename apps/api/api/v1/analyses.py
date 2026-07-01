"""Analysis endpoints (BLUEPRINT.md §2/§3).

Dual-mode: when a Redis + database are configured the upload enqueues a job and
returns a pending analysis to poll; otherwise the engine runs in-request against the
in-memory store (the zero-dependency demo path).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from ai import Narrative, make_explainer, prioritize_analysis
from engine.aggregate import AnalysisAggregate
from engine.models import Finding
from engine.pipeline import AnalysisResult, analyze, pending_result
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from api import report
from api.jobs import async_enabled, enqueue_analysis, get_queue
from api.sample_data import SAMPLE_CSV, SAMPLE_K8S, SAMPLE_TF
from api.security import rate_limit, require_api_key
from api.store import store
from api.v1.schemas import AnalysisSummary, FindingDetail

# Auth + rate limiting are opt-in (no-ops until configured) — see api.security.
router = APIRouter(tags=["analyses"], dependencies=[Depends(require_api_key), Depends(rate_limit)])

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
    terraform: Annotated[UploadFile | None, File()] = None,
    billing: Annotated[UploadFile | None, File()] = None,
    kubernetes: Annotated[UploadFile | None, File()] = None,
) -> AnalysisSummary:
    if terraform is None and kubernetes is None:
        raise HTTPException(status_code=400, detail="upload a terraform and/or kubernetes file")
    tf_text = await _read_text(terraform) if terraform is not None else None
    csv_text = await _read_text(billing) if billing is not None else None
    k8s_text = await _read_text(kubernetes) if kubernetes is not None else None
    meta = {
        "terraform": terraform.filename if terraform else None,
        "billing": billing.filename if billing else None,
        "kubernetes": kubernetes.filename if kubernetes else None,
    }

    if async_enabled():
        # Enqueue: persist a pending record, return immediately; the worker fills it in.
        analysis_id = uuid.uuid4().hex
        store.save(pending_result(analysis_id, meta))
        enqueue_analysis(get_queue(), analysis_id, tf_text, csv_text, k8s_text, meta)
        return AnalysisSummary.from_result(store.get(analysis_id))

    result = analyze(
        explain=_explain,
        terraform_source=tf_text,
        billing_source=csv_text,
        kubernetes_source=k8s_text,
        source_meta=meta,
    )
    store.save(result)
    return AnalysisSummary.from_result(result)


@router.get("/trends")
def get_trends() -> list[dict]:
    """Savings over time — one point per completed analysis (historical trend)."""
    return store.trend()


@router.post("/analyses/sample", status_code=201, response_model=AnalysisSummary)
def create_sample_analysis() -> AnalysisSummary:
    """Instant-demo: run the engine on the bundled sample dataset (no upload)."""
    result = analyze(
        explain=_explain,
        terraform_source=SAMPLE_TF,
        billing_source=SAMPLE_CSV,
        kubernetes_source=SAMPLE_K8S,
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


@router.get("/analyses/{analysis_id}/summary", response_model=AnalysisAggregate)
def get_summary(analysis_id: str) -> AnalysisAggregate:
    """Aggregated view: realistic (deduped) vs gross savings, by-detector, top ops."""
    result = store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return result.aggregate


@router.get("/analyses/{analysis_id}/narrative", response_model=Narrative)
def get_narrative(analysis_id: str) -> Narrative:
    """Architect-voice prioritization narrative for the whole analysis."""
    result = store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return prioritize_analysis(result.aggregate)


def _require(analysis_id: str) -> AnalysisResult:
    result = store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return result


@router.get("/analyses/{analysis_id}/report.md")
def report_markdown(analysis_id: str) -> Response:
    result = _require(analysis_id)
    md = report.to_markdown(result, prioritize_analysis(result.aggregate))
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="cloudtrim-{analysis_id}.md"'},
    )


@router.get("/analyses/{analysis_id}/report.pdf")
def report_pdf(analysis_id: str) -> Response:
    result = _require(analysis_id)
    try:
        pdf = report.to_pdf(result, prioritize_analysis(result.aggregate))
    except ImportError as exc:  # optional [reports] extra not installed
        raise HTTPException(
            status_code=501, detail="PDF export unavailable: install the [reports] extra"
        ) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cloudtrim-{analysis_id}.pdf"'},
    )


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
