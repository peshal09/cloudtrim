# GitHub App setup

CloudTrim reviews Terraform pull requests: on a PR touching `.tf` it comments the
cost impact and waste, and on `/cloudtrim fix` it opens a ready-to-merge PR that
rightsizes the resources with validated HCL. This is the shift-left differentiator
(BLUEPRINT.md §3 Week 4).

## What it does

1. **PR opened / updated** → CloudTrim analyzes the changed Terraform and posts a
   comment: total realizable savings + a per-finding table.
2. **`/cloudtrim fix` comment** on the PR → CloudTrim branches from the PR head,
   commits the rightsized files, and opens a fix PR with an engine-grounded
   description (every dollar figure computed by the engine, not the LLM).

All GitHub writes are reviewable PRs/comments — CloudTrim never force-pushes or
auto-executes.

## Create the App

1. GitHub → **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. **Webhook URL:** `https://<your-host>/api/v1/github/webhook`
   (for local dev, expose the API with `ngrok http 8000` and use the ngrok URL).
3. **Webhook secret:** generate a random string; you'll set it as
   `CLOUDTRIM_GITHUB_WEBHOOK_SECRET`.
4. **Repository permissions:**
   - Contents: **Read & write** (read `.tf`, commit the fix branch)
   - Pull requests: **Read & write** (comment, open the fix PR)
5. **Subscribe to events:** Pull request, Issue comment.
6. Install the App on the target repository.

## Configure CloudTrim

Set two environment variables on the API (see `.env.example`):

```bash
CLOUDTRIM_GITHUB_WEBHOOK_SECRET=<the webhook secret from step 3>
CLOUDTRIM_GITHUB_TOKEN=<an App installation token or a PAT>
```

- `CLOUDTRIM_GITHUB_WEBHOOK_SECRET` gates the webhook — every delivery is
  HMAC-SHA256 verified against it, so the endpoint is safe to expose publicly.
- `CLOUDTRIM_GITHUB_TOKEN` is the bearer used for the REST API. The simplest working
  value is a **PAT** (fine-grained, Contents + Pull requests read/write) or a
  short-lived **App installation access token**. Minting an installation token from
  the App's private key (JWT → `POST /app/installations/{id}/access_tokens`) is the
  production path; wire that into your secrets management and refresh hourly.

Without `CLOUDTRIM_GITHUB_TOKEN` the webhook returns `503` (no client configured) —
by design, so a misconfigured deploy fails loud rather than silently.

## How safety is enforced

- **Signature verification** — `X-Hub-Signature-256` HMAC-SHA256, constant-time
  compared (`api/github/signature.py`). A bad signature is `401`.
- **Idempotency** — redeliveries (same `X-GitHub-Delivery`) are deduped, so GitHub's
  at-least-once delivery doesn't double-comment. (In-memory for now; a shared
  Redis/DB set makes this correct across replicas.)
- **Validated HCL** — generated patches are re-parsed (and `terraform validate`'d
  when the binary is present) before a fix PR is opened.

## Local demo without a real repo

The whole flow is covered by `apps/api/tests/test_github.py` using a fake GitHub
client — signature rejection, the cost comment, idempotent redelivery, and the
`/cloudtrim fix` PR (branch + commit + PR). Run `make test` to see it end to end
with no GitHub account.
