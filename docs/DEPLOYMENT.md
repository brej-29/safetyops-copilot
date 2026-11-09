# Deployment and operations

## Primary deployment

- Project: `safetyops-copilot` in Google Cloud.
- Service: `safetyops-api`, region `asia-southeast1`.
- Public website: https://safetyops-api-a5afr3rcdq-as.a.run.app/
- Workspace: `/app`; API: `/api/workspace`; OpenAPI: `/docs`.
- Public content: `/guides/incident-triage`, `/guides/shift-handover`, `/privacy`.
- Legacy console: https://safetyops-copilot.streamlit.app/ (separate deployment).

The website is bundled into the existing Python image and served by FastAPI.
There is no frontend build in production. `scripts/build_web.py` regenerates the
tracked HTML pages; run it after changing its content. Browser test dependencies
are development-only.

## Storage and startup

Production uses the existing configured Postgres database. The API imports the
workspace models before `init_db()` so startup creates additive workspace,
observation and action tables. Existing event tables are not modified. Back up
production storage and use managed migrations before evolving these tables.
SQLite is supported for local work; do not use Cloud Run's ephemeral filesystem
for durable public workspaces.

Workspace assessment is synchronous and independent of Redis and the worker.
The legacy streaming pipeline still requires Redis, worker connectivity and valid
model artifacts. At the upgrade's infrastructure check, production database health
was true and Redis health was false (the previous Upstash endpoint was unavailable).
This release does not claim to have repaired that external service. Replace or
restore the Redis endpoint before advertising live ingestion as operational.

## Build and deploy

Use an account authorized for the existing project. Preserve runtime variables
and secrets; do not pass secrets in command arguments or commit them.

```bash
python scripts/build_web.py
pytest -q
ruff check .
gcloud run deploy safetyops-api --source . --project safetyops-copilot \
  --region asia-southeast1 --no-traffic --tag workspace-review
```

This creates a revision while leaving existing traffic on its current revision.
Test the returned tagged URL first. Promote the verified revision explicitly:

```bash
gcloud run services update-traffic safetyops-api --project safetyops-copilot \
  --region asia-southeast1 --to-revisions VERIFIED_REVISION=100
```

Use the literal revision returned by Cloud Run. Do not run these examples with the
placeholder unchanged. Existing CPU/memory/max-scale settings are retained.
Cloud Run, its builds, artifact storage and database can incur charges; no
zero-cost or uptime guarantee is claimed.

`.gcloudignore` and `.dockerignore` exclude local credentials, `.env`, virtual
environments, node_modules, generated databases, private uploads and model binaries.
Model downloads remain best-effort via the existing startup script.

## Acceptance checks

1. Public pages, font, CSS, scripts, mark and social image return HTTP 200.
2. `robots.txt`, `sitemap.xml` and `llms.txt` expose only intended public content.
3. `/app` and `/api/workspace` have noindex; workspace data has `Cache-Control: no-store`.
4. Create a new browser workspace, save an observation and an action, reload,
   close with evidence, export and delete the disposable test workspace.
5. A second browser context cannot access the first context's records.
6. HTTPS workspace cookies are Secure, HttpOnly and SameSite=Strict.
7. Separately inspect `/system/status` for the optional streaming components.

`/health` is a liveness check and does not prove Redis, worker or database health.

## Rollback and known boundaries

Record the prior traffic revision before promotion. Roll back with the same
`update-traffic` command pointing 100% at that revision. Additive workspace tables
can remain; rolling back code does not delete user records. Never drop them as a
rollback shortcut.

The public limiter is an in-process 40-mutation/minute peer window, with bounded
memory. It is not a distributed, per-account quota. Workspace size is capped at
500 observations and 1,000 actions. Browser access lasts up to one year, but
cookie expiry does not delete server data. Automatic retention cleanup, recovery,
team accounts, notifications, backup restoration and file-evidence uploads are
not implemented.

## Local verification

```bash
# Set SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db in your shell or .env.
uvicorn apps.api.main:app --host 127.0.0.1 --port 8010
# Another terminal:
npm ci
npx playwright install chromium
npm run test:web
```

`npm run test:web` creates and deletes disposable records in its test browser.
Use a dedicated test environment for ongoing CI. Keep the local preview on
loopback unless you intentionally need network access.

## Source-only patch option

When dependencies are unchanged, `Dockerfile.web-patch` can layer updated apps
and safetyops sources onto a verified runtime image. The pinned base digest and
output image are explicit substitutions in `infra/cloudbuild-web-patch.yaml`.
Build with `gcloud builds submit --config infra/cloudbuild-web-patch.yaml`; inspect
the resulting image, then deploy that image to a non-traffic revision as above.
Use the normal Dockerfile for dependency changes or a fresh installation. This
patch path is project-specific and requires access to the referenced registry.

Cloud mode forces workspace cookies to Secure even when Cloud Run's internal
request scheme is HTTP after HTTPS termination. Local loopback development still
works over HTTP. Origin validation compares the browser origin with the requested
host, and SameSite=Strict applies in both modes.

Optional NLP artifacts warm in a background thread after API startup. Workspace
assessment does not synchronously load a model: it uses the explicit rule fallback
until the model is ready. Existing saved records retain their original assessment
and provenance. Legacy ingestion/MCP inference can still load the model on demand.

## Verified current release

2026-11-09: revision `safetyops-api-00010-tag` serves 100% of the primary URL.
The tagged revision passed the complete browser workflow before promotion, and
main public pages plus private-cookie creation were rechecked afterward.
Rollback target: `safetyops-api-00008-feq`. See HANDOFF.md for the acceptance record.
