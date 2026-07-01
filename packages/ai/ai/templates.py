"""Deterministic architect-voice-lite explanation (BLUEPRINT.md §6).

This is not a degraded stub — it is proof of the core thesis: CloudTrim produces
correct, readable findings with zero LLM, so the model is genuinely additive, not
a wrapper. Populated from the same structured evidence the LLM receives; every
dollar figure is an engine number (so it passes validation by construction).
"""

from __future__ import annotations

from engine.models import Finding, Resource


def _money(value: float) -> str:
    return f"${value:,.2f}"


def render_template(finding: Finding, resource: Resource | None) -> str:
    ident = resource.identifier if resource else finding.resource_id
    rtype = resource.type.value.upper() if resource else "Resource"
    ev = finding.evidence
    action = ev.get("action")
    parts: list[str] = []

    if action == "rightsize":
        cur = ev.get("current_instance_type")
        tgt = ev.get("target_instance_type")
        cpu = ev.get("cpu_pct")
        if cpu is not None:
            parts.append(
                f"{rtype} `{ident}` is averaging {cpu}% CPU, well under the "
                f"{ev.get('threshold_pct')}% threshold."
            )
        else:
            parts.append(
                f"{rtype} `{ident}` is a {cur} declared in Terraform with no "
                f"utilization data to justify its size."
            )
        parts.append(
            f"Rightsizing {cur} → {tgt} lowers the on-demand cost from "
            f"{_money(finding.current_cost)} to {_money(finding.projected_cost)}/mo, "
            f"saving {_money(finding.monthly_savings)}/mo."
        )

    elif action == "delete":
        parts.append(f"{rtype} `{ident}` is a deletion candidate: {ev.get('reason', 'unused')}.")
        parts.append(f"Removing it saves {_money(finding.current_cost)}/mo.")

    elif action == "review":  # K8s tuning finding (over-request, replica over-provisioning)
        note = ev.get("note")
        parts.append(f"`{ident}`: {note}." if note else f"`{ident}`: {finding.title.lower()}.")
        parts.append("No dollar figure is attached (node-cost attribution is future work).")

    elif action == "governance":
        issues = ev.get("issues")
        if issues:
            parts.append(f"`{ident}` has governance gaps: {'; '.join(issues)}.")
            parts.append(
                "No direct dollar impact, but it weakens cost allocation and change safety."
            )
        else:  # e.g. missing S3 lifecycle — a note-based hygiene finding
            note = ev.get("note")
            detail = f" — {note}" if note else ""
            parts.append(f"`{ident}`: {finding.title.lower()}{detail}.")
            parts.append("No savings are computed here, but it's worth fixing as hygiene.")

    else:
        parts.append(f"`{ident}`: {finding.title}.")

    parts.append(f"Estimated rollout risk is {finding.risk.value}.")
    return " ".join(parts)
