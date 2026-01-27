from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
from evidently.metric_preset import DataDriftPreset, TextDriftPreset
from evidently.report import Report

from safetyops.core.logging import get_logger
from safetyops.core.settings import settings
from safetyops.db import EnrichedEvent
from safetyops.db.session import get_session

logger = get_logger(__name__)

DRIFT_REPORT_DIR = Path(settings.artifacts_dir) / "drift_reports"
DEFAULT_REFERENCE_DATA_PATH = Path("data/text/incidents_synthetic.csv")


def _load_reference_data(path: Path = DEFAULT_REFERENCE_DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Reference dataset not found at {path}. "
            "Run `python scripts/download_text_dataset.py` first."
        )
    df = pd.read_csv(path)
    if "text" not in df.columns or "severity" not in df.columns:
        raise ValueError("Reference dataset must contain 'text' and 'severity' columns.")
    df = df.copy()
    df["severity_numeric"] = df["severity"].map({"low": 0, "medium": 1, "high": 2}).fillna(0)
    df["text_length"] = df["text"].astype(str).str.len()
    return df[["text", "severity_numeric", "text_length"]]


def _load_current_data(limit: int = 500) -> pd.DataFrame:
    with get_session() as session:
        rows = (
            session.query(EnrichedEvent)
            .filter(EnrichedEvent.event_type == "text")
            .order_by(EnrichedEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    if not rows:
        raise ValueError("No enriched text events available for drift analysis.")

    texts = []
    severities = []
    lengths = []
    for row in rows:
        enrichment = row.enrichment or {}
        text = enrichment.get("text") or enrichment.get("summary") or ""
        severity = enrichment.get("severity") or row.severity or "low"
        texts.append(str(text))
        severities.append(severity)
        lengths.append(len(str(text)))

    df = pd.DataFrame(
        {
            "text": texts,
            "severity_numeric": pd.Series(severities).map({"low": 0, "medium": 1, "high": 2}).fillna(0),
            "text_length": lengths,
        }
    )
    return df


def build_drift_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    output_path: Path,
) -> None:
    """Build a combined text + numeric drift report and save as HTML."""
    report = Report(metrics=[TextDriftPreset(column_name="text"), DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(output_path))


def run_drift_analysis() -> Path:
    """High-level API used by the REST endpoint and UI.

    Loads reference data (training set) and recent production events, generates
    an Evidently drift report, and returns the HTML path.
    """
    reference = _load_reference_data()
    current = _load_current_data()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = DRIFT_REPORT_DIR / f"text_drift_{ts}.html"

    logger.info(
        "Running Evidently drift analysis",
        extra={
            "reference_rows": len(reference),
            "current_rows": len(current),
            "output_path": str(output_path),
        },
    )
    build_drift_report(reference, current, output_path)
    return output_path


def get_latest_report_path() -> Path | None:
    if not DRIFT_REPORT_DIR.exists():
        return None
    reports = sorted(DRIFT_REPORT_DIR.glob("text_drift_*.html"))
    return reports[-1] if reports else None