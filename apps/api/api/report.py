"""Report export — Markdown + PDF (BLUEPRINT.md §3 Week 2).

Renders a completed analysis into a shareable report: the prioritization narrative,
the deduped savings summary, and every finding with its explanation and proposed
change. Markdown is always available; PDF needs the optional [reports] extra (fpdf2,
pure-Python).
"""

from __future__ import annotations

from ai import Narrative
from engine.pipeline import AnalysisResult


def _money(v: float) -> str:
    return f"${v:,.2f}"


def to_markdown(result: AnalysisResult, narrative: Narrative) -> str:
    agg = result.aggregate
    a = result.analysis
    lines = [
        "# CloudTrim Report",
        "",
        f"Analysis `{a.id}` · {a.created_at:%Y-%m-%d %H:%M UTC}",
        "",
        "## Summary",
        "",
        f"- **Realizable savings:** {_money(agg.realistic_monthly_savings)}/mo "
        f"(gross {_money(agg.gross_monthly_savings)}/mo)",
        f"- **Findings:** {len(result.findings)} "
        f"(high {agg.severity_counts['high']}, "
        f"medium {agg.severity_counts['medium']}, low {agg.severity_counts['low']})",
        "",
        "## Prioritization",
        "",
        narrative.text,
        "",
        "## Findings",
        "",
        "| Detector | Resource | Severity | Risk | Savings/mo |",
        "|---|---|---|---|---|",
    ]
    by_id = {r.id: r for r in result.resources}
    ordered = sorted(result.findings, key=lambda f: (-f.monthly_savings, f.severity))
    for f in ordered:
        ident = by_id[f.resource_id].identifier if f.resource_id in by_id else f.resource_id
        savings = _money(f.monthly_savings) if f.monthly_savings > 0 else "—"
        lines.append(
            f"| {f.detector} | `{ident}` | {f.severity.value} | {f.risk.value} | {savings} |"
        )

    lines += ["", "## Details", ""]
    for f in ordered:
        ident = by_id[f.resource_id].identifier if f.resource_id in by_id else f.resource_id
        lines += [f"### {f.title} — `{ident}`", "", f.explanation or "", ""]
        if f.remediation_diff:
            lines += ["```hcl", f.remediation_diff, "```", ""]
    return "\n".join(lines)


def _pdf_safe(text: str) -> str:
    # Core PDF fonts are latin-1; map the few unicode chars we emit.
    for bad, good in (("→", "->"), ("—", "-"), ("’", "'"), ("•", "-")):
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def to_pdf(result: AnalysisResult, narrative: Narrative) -> bytes:
    from fpdf import FPDF  # lazy: optional [reports] dependency

    agg = result.aggregate
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "CloudTrim Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(120)
    pdf.cell(0, 6, _pdf_safe(f"Analysis {result.analysis.id}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(3)

    def heading(text: str) -> None:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)

    # multi_cell defaults to leaving x at the right margin; reset to the left each
    # time so the next block has full page width.
    def para(text: str, h: float = 6) -> None:
        pdf.multi_cell(pdf.epw, h, _pdf_safe(text), new_x="LMARGIN", new_y="NEXT")

    heading("Summary")
    para(
        f"Realizable savings: {_money(agg.realistic_monthly_savings)}/mo "
        f"(gross {_money(agg.gross_monthly_savings)}/mo)\n"
        f"Findings: {len(result.findings)} "
        f"(high {agg.severity_counts['high']}, medium {agg.severity_counts['medium']}, "
        f"low {agg.severity_counts['low']})"
    )
    pdf.ln(2)

    heading("Prioritization")
    para(narrative.text)
    pdf.ln(2)

    heading("Findings")
    by_id = {r.id: r for r in result.resources}
    for f in sorted(result.findings, key=lambda f: (-f.monthly_savings, f.severity)):
        ident = by_id[f.resource_id].identifier if f.resource_id in by_id else f.resource_id
        savings = _money(f.monthly_savings) if f.monthly_savings > 0 else "no direct savings"
        pdf.set_font("Helvetica", "B", 11)
        para(f"{f.title} - {ident}  [{savings}]")
        pdf.set_font("Helvetica", size=10)
        para(f.explanation or "", h=5)
        pdf.ln(2)

    return bytes(pdf.output())
