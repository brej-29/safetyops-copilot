from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATA_DIR = Path("data/text")
OUTPUT_PATH = DATA_DIR / "incidents_synthetic.csv"


@dataclass
class IncidentExample:
    text: str
    category: str
    severity: str


CATEGORIES = {
    "fall": [
        "Worker slipped on a wet floor near the loading dock.",
        "Employee tripped over loose cables and fell down the stairs.",
        "Contractor fell from a ladder while checking inventory.",
    ],
    "electrical": [
        "Technician received an electrical shock while repairing a panel.",
        "Exposed wiring discovered near the main switchboard.",
        "Sparks observed from overloaded extension cords.",
    ],
    "fire": [
        "Small fire broke out near the welding station.",
        "Smoke detected in the server room due to overheating equipment.",
        "Burn marks found around improperly stored flammable materials.",
    ],
    "chemical": [
        "Chemical spill reported in the maintenance room.",
        "Strong gas odor detected near the storage tanks.",
        "Employee splashed with cleaning acid while refilling containers.",
    ],
    "ppe_noncompliance": [
        "Worker entered the construction zone without a hard hat.",
        "Operator handling chemicals without safety goggles.",
        "Employee observed in loading area without high-visibility vest.",
    ],
    "other": [
        "Near miss reported in warehouse traffic area.",
        "Unsecured tools discovered on elevated platform.",
        "General housekeeping issues noted in production area.",
    ],
}

SEVERITIES = {
    "low": [
        "No injury reported.",
        "No medical treatment required.",
        "Minor issue resolved on site.",
    ],
    "medium": [
        "Minor injury requiring first aid.",
        "Short work stoppage for investigation.",
        "Employee evaluated by onsite medic.",
    ],
    "high": [
        "Serious injury requiring hospitalization.",
        "Emergency services were called.",
        "Area evacuated due to immediate danger.",
    ],
}


def _generate_examples(n_per_category: int = 50) -> Iterable[IncidentExample]:
    for category, base_texts in CATEGORIES.items():
        for i in range(n_per_category):
            base = base_texts[i % len(base_texts)]
            # Simple pattern to vary severity by index
            if i % 10 == 0:
                severity = "high"
            elif i % 4 == 0:
                severity = "medium"
            else:
                severity = "low"

            severity_suffix = SEVERITIES[severity][i % len(SEVERITIES[severity])]
            text = f"{base} {severity_suffix}"
            yield IncidentExample(text=text, category=category, severity=severity)


def main() -> None:
    """Generate a small synthetic incident dataset for local training and testing.

    This avoids relying on large or licensed external datasets. The generated
    CSV is suitable for quick DistilBERT fine-tuning demonstrations, but it
    should not be treated as real-world safety data.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    examples = list(_generate_examples())
    fieldnames = ["text", "category", "severity"]

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ex in examples:
            writer.writerow(
                {
                    "text": ex.text,
                    "category": ex.category,
                    "severity": ex.severity,
                }
            )

    print(f"Wrote synthetic incident dataset with {len(examples)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()