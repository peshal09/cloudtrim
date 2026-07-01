"""GitHub REST client (BLUEPRINT.md §3 Week 4).

`GitHubClient` is the interface the handler depends on; tests inject a fake, the live
path uses `HttpGitHubClient` (httpx + a bearer token — an App installation token or a
PAT). Only enough of the REST surface for: read a PR's files, comment, and open a fix
PR (branch + commit + PR).
"""

from __future__ import annotations

import base64
from typing import Any, Protocol

from api.settings import settings


class GitHubClient(Protocol):
    def get_pr(self, repo: str, number: int) -> dict: ...
    def list_pr_files(self, repo: str, number: int) -> list[dict]: ...
    def get_file(self, repo: str, path: str, ref: str) -> str: ...
    def post_comment(self, repo: str, number: int, body: str) -> None: ...
    def create_branch(self, repo: str, from_sha: str, new_branch: str) -> None: ...
    def put_file(self, repo: str, path: str, content: str, branch: str, message: str) -> None: ...
    def create_pull_request(
        self, repo: str, head: str, base: str, title: str, body: str
    ) -> str: ...


class HttpGitHubClient:
    def __init__(self, token: str, api_url: str) -> None:
        import httpx

        self._http = httpx.Client(
            base_url=api_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20,
        )

    def _json(self, method: str, path: str, **kw: Any) -> Any:
        resp = self._http.request(method, path, **kw)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def get_pr(self, repo: str, number: int) -> dict:
        return self._json("GET", f"/repos/{repo}/pulls/{number}")

    def list_pr_files(self, repo: str, number: int) -> list[dict]:
        return self._json("GET", f"/repos/{repo}/pulls/{number}/files")

    def get_file(self, repo: str, path: str, ref: str) -> str:
        data = self._json("GET", f"/repos/{repo}/contents/{path}", params={"ref": ref})
        return base64.b64decode(data["content"]).decode()

    def post_comment(self, repo: str, number: int, body: str) -> None:
        self._json("POST", f"/repos/{repo}/issues/{number}/comments", json={"body": body})

    def create_branch(self, repo: str, from_sha: str, new_branch: str) -> None:
        self._json(
            "POST",
            f"/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{new_branch}", "sha": from_sha},
        )

    def put_file(self, repo: str, path: str, content: str, branch: str, message: str) -> None:
        existing = self._http.get(f"/repos/{repo}/contents/{path}", params={"ref": branch})
        sha = existing.json().get("sha") if existing.status_code == 200 else None
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        self._json("PUT", f"/repos/{repo}/contents/{path}", json=payload)

    def create_pull_request(self, repo: str, head: str, base: str, title: str, body: str) -> str:
        pr = self._json(
            "POST",
            f"/repos/{repo}/pulls",
            json={"head": head, "base": base, "title": title, "body": body},
        )
        return pr.get("html_url", "")


def get_github_client() -> GitHubClient | None:
    """Live client when a token is configured; None otherwise (tests inject a fake)."""
    if not settings.github_token:
        return None
    return HttpGitHubClient(settings.github_token, settings.github_api_url)
