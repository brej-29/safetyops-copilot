from __future__ import annotations

from pathlib import Path

from safetyops.core.logging import get_logger

logger = get_logger(__name__)

_RUNBOOKS_DIR = Path(__file__).parent


def _load_markdown(name: str) -> str:
    path = _RUNBOOKS_DIR / f"{name}.md"
    if not path.exists():
        logger.warning("Runbook file not found", extra={"path": str(path)})
        return "No specific runbook available for this category yet."
    return path.read_text(encoding="utf-8")


def load_runbook_for_category(category: str) -> str:
    """Load a markdown runbook for the given incident category."""
    key = category.lower()
    if "fall" in key:
        return _load_markdown("falls")
    if "electric" in key:
        return _load_markdown("electrical")
    if "fire" in key or "smoke" in key:
        return _load_markdown("fire")
    if "chemical" in key or "spill" in key:
        return _load_markdown("chemical")
    if "ppe" in key or "compliance" in key:
        return _load_markdown("ppe_noncompliance")
    return _load_markdown("generic")