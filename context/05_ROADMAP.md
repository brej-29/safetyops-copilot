# Roadmap — SafetyOps Copilot

Updated 2026-11-09. Current product intent: ../PRODUCT.md.

## Delivered foundations

- Event ingestion, Redis Streams worker, SQL persistence and aggregate queries.
- DistilBERT severity training/evaluation on MSHA data, YOLO hard-hat integration.
- LangGraph triage, runbooks, optional LLM enhancement, retries/DLQ and monitoring.
- Docker local infrastructure and a deployed Cloud Run API.

## Delivered coordinator workspace

- Same-origin responsive website with crawlable public guides and metadata.
- Isolated browser-linked SQL workspaces, observation register and clear provenance.
- Corrective-action ownership, due dates, evidence-gated closure and revision history.
- Markdown/CSV/JSON exports and a separated synthetic demonstration.
- Read-only local MCP server with shared assessment logic and protocol tests.
- Desktop/mobile/keyboard browser regression checks and CI automation.
- Visual README, real product media, design system and complete portfolio handoff.

## Next useful work

- Restore the unavailable external Redis endpoint and verify the legacy worker.
- Gather coordinator feedback; measure actual return use before claiming retention.
- Add recoverable identity/cross-device access, then team roles if demanded.
- Add database migrations and retention cleanup before changing production schema.
- Validate prospective utility, domain transfer and severity calibration.
- Add notifications only with a reliable identity/delivery model.
- Implement archive restore and tested backup recovery if users need it.
- Verify Search Console ownership and inspect indexing; consider a custom domain.

Unimplemented features are not claims in the README or handoff. See HANDOFF.md
for evidence, limitations and the final deployment acceptance record.
