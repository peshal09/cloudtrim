"""Webhook event handling (BLUEPRINT.md §3 Week 4).

On a PR touching `.tf`: analyze the changed Terraform and post a cost + waste comment.
On a `/cloudtrim fix` comment: open a fix PR that commits the rightsized files with an
architect-written description. All GitHub access goes through the injected client, so
this is fully testable with a fake.
"""

from __future__ import annotations

from ai import describe_pr, make_explainer
from engine.pipeline import analyze
from engine.remediation import rewrite_tf

from api.github.client import GitHubClient

_PR_ACTIONS = {"opened", "synchronize", "reopened"}
_FIX_COMMAND = "/cloudtrim fix"
_explain = make_explainer()


def handle_event(event: str, payload: dict, client: GitHubClient) -> dict:
    if event == "pull_request":
        return handle_pull_request(payload, client)
    if event == "issue_comment":
        return handle_comment(payload, client)
    return {"status": "ignored", "event": event}


def _terraform_from_pr(repo: str, number: int, sha: str, client: GitHubClient) -> str | None:
    tf_files = [
        f["filename"] for f in client.list_pr_files(repo, number) if f["filename"].endswith(".tf")
    ]
    if not tf_files:
        return None
    return "\n".join(client.get_file(repo, path, sha) for path in tf_files)


def handle_pull_request(payload: dict, client: GitHubClient) -> dict:
    if payload.get("action") not in _PR_ACTIONS:
        return {"status": "ignored", "action": payload.get("action")}
    repo = payload["repository"]["full_name"]
    pr = payload["pull_request"]
    number, sha = pr["number"], pr["head"]["sha"]

    tf = _terraform_from_pr(repo, number, sha, client)
    if tf is None:
        return {"status": "no_terraform"}

    result = analyze(terraform_source=tf, explain=_explain)
    client.post_comment(repo, number, _render_comment(result))
    return {
        "status": "commented",
        "findings": len(result.findings),
        "savings": result.analysis.total_monthly_savings,
    }


def handle_comment(payload: dict, client: GitHubClient) -> dict:
    if payload.get("action") != "created":
        return {"status": "ignored"}
    if _FIX_COMMAND not in payload.get("comment", {}).get("body", ""):
        return {"status": "ignored"}
    if "pull_request" not in payload.get("issue", {}):
        return {"status": "not_a_pr"}
    repo = payload["repository"]["full_name"]
    number = payload["issue"]["number"]
    return open_fix_pr(repo, number, client)


def open_fix_pr(repo: str, number: int, client: GitHubClient) -> dict:
    pr = client.get_pr(repo, number)
    head_ref, head_sha = pr["head"]["ref"], pr["head"]["sha"]
    tf_files = [
        f["filename"] for f in client.list_pr_files(repo, number) if f["filename"].endswith(".tf")
    ]

    fix_branch = f"cloudtrim/fix-{number}"
    client.create_branch(repo, head_sha, fix_branch)

    fixed = []
    for path in tf_files:
        content = client.get_file(repo, path, head_sha)
        patched = content
        for f in analyze(terraform_source=content).findings:
            new = rewrite_tf(f, patched)
            if new is not None:
                patched = new
                fixed.append(f)
        if patched != content:
            client.put_file(repo, path, patched, fix_branch, "CloudTrim: rightsize resources")

    if not fixed:
        return {"status": "nothing_to_fix"}

    desc = describe_pr(fixed)
    url = client.create_pull_request(repo, fix_branch, head_ref, desc.title, desc.body)
    return {"status": "pr_opened", "url": url, "fixes": len(fixed)}


def _render_comment(result) -> str:
    a = result.analysis
    priced = [f for f in result.findings if f.monthly_savings > 0]
    if not result.findings:
        return "### CloudTrim\n\n✅ No cost issues found in the Terraform changes."
    lines = [
        "### CloudTrim — cost review",
        "",
        f"Found **{len(result.findings)}** issue(s), "
        f"**${a.total_monthly_savings:,.2f}/mo** in realizable savings.",
        "",
        "| Detector | Resource | Severity | Savings/mo |",
        "|---|---|---|---|",
    ]
    by_id = {r.id: r for r in result.resources}
    for f in sorted(result.findings, key=lambda f: -f.monthly_savings):
        ident = by_id[f.resource_id].identifier if f.resource_id in by_id else f.resource_id
        savings = f"${f.monthly_savings:,.2f}" if f.monthly_savings > 0 else "—"
        lines.append(f"| {f.detector} | `{ident}` | {f.severity.value} | {savings} |")
    if priced:
        lines += ["", f"Comment `{_FIX_COMMAND}` and I'll open a PR with the fixes."]
    return "\n".join(lines)
