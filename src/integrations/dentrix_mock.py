"""Mock Dentrix integration — mimics the Dentrix API surface for local development.

In-memory only, by design. A real PMS integration must never persist patient
data locally: fetch on demand, hold it for the current session, write back to
the PMS, keep nothing. This mock mirrors that contract now so nothing has to
change when DentrixMock is swapped for a real PMS adapter later — see
docs/PRODUCTION_PATH.md (Milestone 2, PHI handling audit).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.config import MOCK_CASES_DIR

_SEED_DIR = MOCK_CASES_DIR.parent / "mock_charts"


class DentrixMock:
    """
    Stub that simulates read/write operations against a Dentrix patient chart.

    Storage is a plain in-memory dict, scoped to this instance — nothing is
    ever written to disk. Optionally seeds itself from static, checked-in
    fixture JSON (synthetic data only) for demo purposes; those files are
    read once at construction and never written back to.
    """

    def __init__(self, seed_dir: Path | None = None) -> None:
        self._charts: dict[str, dict] = {}
        seed_dir = seed_dir if seed_dir is not None else _SEED_DIR
        if seed_dir.exists():
            for path in seed_dir.glob("*.json"):
                try:
                    chart = json.loads(path.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                patient_id = chart.get("patient_id", path.stem)
                self._charts[patient_id] = chart

    def get_chart(self, patient_id: str) -> dict:
        return self._charts.get(
            patient_id,
            {"patient_id": patient_id, "teeth": {}, "notes": [], "procedures": []},
        )

    def write_chart_entry(self, patient_id: str, entry: dict) -> dict:
        chart = self.get_chart(patient_id)
        entry["timestamp"] = date.today().isoformat()

        if entry.get("entry_type") == "procedure":
            chart.setdefault("procedures", []).append(entry)
        elif entry.get("entry_type") == "finding" and entry.get("tooth"):
            tooth_key = str(entry["tooth"])
            chart.setdefault("teeth", {}).setdefault(tooth_key, {})
            chart["teeth"][tooth_key].setdefault("findings", []).append(entry.get("description", ""))
        else:
            chart.setdefault("notes", []).append(entry)

        self._charts[patient_id] = chart
        return {"status": "written", "patient_id": patient_id, "entry": entry}

    def get_treatment_plan(self, patient_id: str) -> list[dict]:
        chart = self.get_chart(patient_id)
        return chart.get("proposed_treatment", [])

    def list_patients(self) -> list[str]:
        return list(self._charts.keys())
