import hashlib
import hmac
import json

import pytest
from api.main import app
from api.settings import settings
from api.v1 import github as gh
from fastapi.testclient import TestClient

SECRET = "test-secret"

# A PR touching a .tf that declares an oversized instance (config-only detector,
# fires without billing) -> a rightsize patch.
PR_TF = """resource "aws_instance" "big" {
  instance_type = "c5.4xlarge"
  tags = {
    env   = "prod"
    owner = "team"
  }
}
"""


class FakeGitHub:
    def __init__(self):
        self.comments = []
        self.branches = []
        self.puts = []
        self.prs = []

    def get_pr(self, repo, number):
        return {"head": {"ref": "feature", "sha": "abc123"}, "base": {"ref": "main"}}

    def list_pr_files(self, repo, number):
        return [{"filename": "main.tf"}, {"filename": "README.md"}]

    def get_file(self, repo, path, ref):
        return PR_TF

    def post_comment(self, repo, number, body):
        self.comments.append(body)

    def create_branch(self, repo, from_sha, new_branch):
        self.branches.append(new_branch)

    def put_file(self, repo, path, content, branch, message):
        self.puts.append((path, content))

    def create_pull_request(self, repo, head, base, title, body):
        self.prs.append({"head": head, "base": base, "title": title, "body": body})
        return "https://github.com/acme/repo/pull/2"


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", SECRET)
    f = FakeGitHub()
    app.dependency_overrides[gh.get_client] = lambda: f
    gh._seen_deliveries.clear()
    yield f
    app.dependency_overrides.clear()


client = TestClient(app)


def _post(event, payload, delivery="d1", secret=SECRET):
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/api/v1/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": event,
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )


def test_invalid_signature_rejected(fake):
    resp = _post("ping", {}, secret="wrong-secret")
    assert resp.status_code == 401


def test_pull_request_posts_cost_comment(fake):
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/repo"},
        "pull_request": {"number": 7, "head": {"ref": "feature", "sha": "abc123"}},
    }
    resp = _post("pull_request", payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "commented"
    assert len(fake.comments) == 1
    assert "CloudTrim" in fake.comments[0]
    assert "$248.20" in fake.comments[0]  # oversized c5.4xlarge -> c5.2xlarge


def test_duplicate_delivery_is_idempotent(fake):
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/repo"},
        "pull_request": {"number": 7, "head": {"ref": "f", "sha": "s"}},
    }
    _post("pull_request", payload, delivery="dup")
    resp = _post("pull_request", payload, delivery="dup")
    assert resp.json()["status"] == "duplicate"
    assert len(fake.comments) == 1  # processed once


def test_fix_command_opens_pr(fake):
    payload = {
        "action": "created",
        "repository": {"full_name": "acme/repo"},
        "issue": {"number": 7, "pull_request": {"url": "..."}},
        "comment": {"body": "please /cloudtrim fix this"},
    }
    resp = _post("issue_comment", payload, delivery="fix1")
    assert resp.json()["status"] == "pr_opened"
    assert fake.branches == ["cloudtrim/fix-7"]
    assert fake.puts and 'instance_type = "c5.2xlarge"' in fake.puts[0][1]
    assert fake.prs and "$248.20" in fake.prs[0]["body"]
