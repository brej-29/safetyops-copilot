# SafetyOps Copilot

<!-- impeccable:product-schema 1 -->

## Platform

Web. An existing Python FastAPI, Redis Streams, SQLAlchemy/Postgres, LangGraph,
DistilBERT, YOLO and Streamlit project. The new primary website is served by
FastAPI; the legacy Streamlit console remains available.

## Users

Confirmed by the user: individual safety
coordinators who record observations and return each shift to follow up actions.
Shared team accounts are not part of this release.
Developers and portfolio reviewers are a secondary audience.

## Product Purpose

Turn a safety observation into a reviewable assessment, owned corrective actions,
and an exportable shift handover. A useful recurring workflow is the user's
explicit goal, alongside a stronger interface and portfolio documentation.

## Capabilities and Constraints

Preserve the existing ingestion, worker, ML and monitoring paths. Model outputs
are decision support and require human review. Historical MSHA evaluation is
evidence for one dataset, not a guarantee of performance on a visitor's site.
Public demo data must be labeled and separated from personal records. Browser
workspaces use opaque credentials and durable database storage; cross-device
team authentication is outside this release. Never expose deployment secrets.

## Brand Commitments

Keep SafetyOps Copilot and the real model evidence. The user delegated creative
and technical decisions and requested animation, SEO, deployment, a visual README,
repository topics and a complete project handoff.

## Evidence on Hand

Existing code, model cards, eval_results.json (1,605 held-out examples), ADRs,
CI and an existing Cloud Run service in project safetyops-copilot.
