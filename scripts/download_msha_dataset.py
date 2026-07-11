"""Download and prepare the MSHA accident-narrative dataset for severity training.

Source: MSHA open data (Mine Accident, Injury and Illness Report form 7000-1),
https://arlweb.msha.gov/OpenGovernmentData/OGIMSHA.asp — all accidents reported
by mine operators and contractors since 1/1/2000, including a free-text
NARRATIVE and a DEGREE_INJURY outcome code.

Severity labels are derived from DEGREE_INJURY_CD:

- high:   01 (fatality), 02 (permanent total/partial disability)
- medium: 03 (days away from work), 04 (days away + restricted),
          05 (restricted activity only)
- low:    00 (accident only, no injury), 06 (no lost days/restrictions),
          10 (all other cases incl. first aid)

Ambiguous codes are excluded: 07 (occupational illness), 08 (natural causes),
09 (non-employees), ? (missing).

The output is a balanced, stratified sample capped at the size of the smallest
class (high, ~3.6k records), split into a training pool and a held-out test
set:

- data/text/incidents_msha.csv       (train/validation pool)
- data/text/incidents_msha_test.csv  (held-out test set; never train on this)

Columns: text, severity, degree_injury_cd
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import random
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MSHA_URL = "https://arlweb.msha.gov/OpenGovernmentData/DataSets/Accidents.zip"
ZIP_PATH = Path("data/text/msha_accidents.zip")
TRAIN_OUT = Path("data/text/incidents_msha.csv")
TEST_OUT = Path("data/text/incidents_msha_test.csv")

SEVERITY_BY_DEGREE = {
    "01": "high",
    "02": "high",
    "03": "medium",
    "04": "medium",
    "05": "medium",
    "00": "low",
    "06": "low",
    "10": "low",
}

MIN_NARRATIVE_CHARS = 30


def download_zip(force: bool = False) -> Path:
    if ZIP_PATH.exists() and not force:
        logger.info("MSHA zip already present; skipping download", extra={"path": str(ZIP_PATH)})
        return ZIP_PATH
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading MSHA accidents dataset", extra={"url": MSHA_URL})
    urllib.request.urlretrieve(MSHA_URL, ZIP_PATH)
    return ZIP_PATH


def extract_records(zip_path: Path) -> dict[str, list[tuple[str, str]]]:
    """Return {severity: [(text, degree_cd), ...]} with deduplicated narratives."""
    by_severity: dict[str, list[tuple[str, str]]] = defaultdict(list)
    seen: set[str] = set()

    with zipfile.ZipFile(zip_path) as z:
        name = z.namelist()[0]
        with z.open(name) as f:
            text_stream = io.TextIOWrapper(f, encoding="latin-1")
            reader = csv.DictReader(text_stream, delimiter="|")
            for row in reader:
                severity = SEVERITY_BY_DEGREE.get((row.get("DEGREE_INJURY_CD") or "").strip())
                if severity is None:
                    continue
                narrative = " ".join((row.get("NARRATIVE") or "").split())
                if len(narrative) < MIN_NARRATIVE_CHARS:
                    continue
                key = narrative.lower()
                if key in seen:
                    continue
                seen.add(key)
                by_severity[severity].append((narrative, row["DEGREE_INJURY_CD"].strip()))

    for severity, records in by_severity.items():
        logger.info(
            "Extracted records", extra={"severity": severity, "count": len(records)}
        )
    return by_severity


def write_csv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "severity", "degree_injury_cd"])
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--per-class-cap",
        type=int,
        default=0,
        help="Max records per class (0 = size of the smallest class).",
    )
    parser.add_argument(
        "--test-fraction", type=float, default=0.15, help="Held-out test fraction."
    )
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    zip_path = download_zip(force=args.force_download)
    by_severity = extract_records(zip_path)

    if not by_severity:
        raise SystemExit("No records extracted; check the source file format.")

    cap = args.per_class_cap or min(len(v) for v in by_severity.values())
    rnd = random.Random(args.seed)

    train_rows: list[tuple[str, str, str]] = []
    test_rows: list[tuple[str, str, str]] = []
    for severity, records in sorted(by_severity.items()):
        rnd.shuffle(records)
        sample = records[:cap]
        n_test = int(len(sample) * args.test_fraction)
        for text, degree in sample[:n_test]:
            test_rows.append((text, severity, degree))
        for text, degree in sample[n_test:]:
            train_rows.append((text, severity, degree))

    rnd.shuffle(train_rows)
    rnd.shuffle(test_rows)
    write_csv(TRAIN_OUT, train_rows)
    write_csv(TEST_OUT, test_rows)

    logger.info(
        "Wrote MSHA severity dataset",
        extra={
            "train_path": str(TRAIN_OUT),
            "train_rows": len(train_rows),
            "test_path": str(TEST_OUT),
            "test_rows": len(test_rows),
            "per_class_cap": cap,
        },
    )


if __name__ == "__main__":
    main()
