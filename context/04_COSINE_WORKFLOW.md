# Cosine Workflow — How Future Tasks Stay Grounded

This document defines how **future AI-assisted work** should interact with this repository so that changes remain consistent, minimal, and well-documented.

---

## 1. Mandatory Reading Order

Before making non-trivial changes, **always**:

1. Read:
   - `context/00_GOAL.md`
   - `context/01_ARCHITECTURE.md`
   - `context/02_COMPONENTS.md`
2. Skim:
   - `context/03_DECISIONS_LOG.md`
   - `context/05_ROADMAP.md`
3. Check:
   - `README.md` (for the latest usage and architecture notes).
   - Relevant notebooks under `notebooks/` if changes touch ML or data assumptions.

If you are an AI agent, treat this as a **hard constraint**.

---

## 2. Principles for Changes

When implementing a new task:

1. **Stay within existing architecture**
   - Prefer extending existing modules over creating parallel ones.
   - Reuse patterns from `safetyops/*` (e.g., logging, settings, metrics).
2. **Small, coherent increments**
   - Each change should have a clear, single responsibility.
   - Avoid broad refactors unless explicitly requested.
3. **Document decisions**
   - If the change introduces:
     - A new dependency,
     - A new external service,
     - A new core pattern (e.g., new stream, new storage),
     then:
       - Add or update an entry in `context/03_DECISIONS_LOG.md`.

---

## 3. Logging, Errors, and Safety

- **Logging**
  - Use `safetyops.core.logging.get_logger` instead of creating ad-hoc loggers.
  - Always include relevant context: `correlation_id`, event id, event type.
- **Exceptions**
  - Avoid bare `except:` blocks.
  - Catch `Exception` only when:
    - You log the error with details, and
    - You can safely continue.
  - Prefer custom exceptions from `safetyops.core.exceptions` when representing domain errors.
- **No secrets**
  - Never commit real secrets.
  - Update `.env.example` to show new configuration knobs.
  - Use env vars with the `SAFETYOPS_` prefix via `Settings`.

---

## 4. Testing and CI

- Add or update **pytest tests** when:
  - You add a new domain model.
  - You modify behavior in event bus, worker, or ML wrappers.
- Keep tests:
  - **Fast** – avoid network or heavy model downloads.
  - **Isolated** – mock out Redis/Postgres/YOLO where appropriate.
- CI expectations:
  - `ruff` passes with the configured rules.
  - `pytest` passes without requiring GPU or large downloads.

If your change requires altering CI behavior (e.g., new tools), document it in:

- `.github/workflows/ci.yml` (with comments)
- `context/03_DECISIONS_LOG.md` if it significantly changes workflows.

---

## 5. Free-first, Local-first

Any new feature must remain:

- **Runnable locally** with:
  - Docker for infra (`infra/docker-compose.local.yml`).
  - Python for services (API, worker, UI).
- **Deployable later on free tiers**:
  - Avoid vendor-specific or paid-only components.
  - Keep resource usage reasonable (CPU-only models, small dependencies where possible).

When adding new dependencies:

1. Consider memory and disk footprint.
2. Justify the addition in `context/03_DECISIONS_LOG.md` if it is heavy or central.

---

## 6. Grounding to Notebooks

If you change ML/data-related behavior:

- Update relevant notebooks in `notebooks/` with:
  - Revised assumptions.
  - Updated planned metrics or EDA ideas.
- Notebooks **do not have to be executed** as part of CI, but must be:
  - Readable.
  - Synchronized with code-level assumptions.

---

## 7. How to Approach a New Task (Checklist)

1. **Understand**:
   - Re-read `context/00_GOAL.md` and `context/01_ARCHITECTURE.md`.
   - Identify which component(s) your task touches.
2. **Plan**:
   - Decide whether changes are in API, worker, UI, or shared libs.
   - Check tests that cover the area and plan additions.
3. **Implement**:
   - Follow existing patterns (settings, logging, metrics).
   - Keep functions small and testable.
4. **Test**:
   - Run `pytest`.
   - Run `ruff`.
5. **Document**:
   - Update `context/03_DECISIONS_LOG.md` if needed.
   - Update `README.md` and notebooks if behavior or flows changed.

Following this workflow keeps SafetyOps Copilot **coherent, maintainable, and AI-friendly** over time.