from __future__ import annotations

from pathlib import Path

import pandas as pd

from safetyops.monitoring.drift import build_drift_report


def test_build_drift_report_smoke(tmp_path: Path) -> None:
    reference = pd.DataFrame(
        {
            "text": ["event one", "event two"],
            "severity_numeric": [0, 2],
            "text_length": [9, 9],
        }
    )
    current = pd.DataFrame(
        {
            "text": ["another event", "yet another"],
            "severity_numeric": [1, 1],
            "text_length": [13, 11],
        }
    )
    out_path = tmp_path / "drift.html"
    build_drift_report(reference, current, out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 0