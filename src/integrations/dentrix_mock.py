"""Mock Dentrix integration — mimics the Dentrix API surface for local development."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.config import MOCK_CASES_DIR


class DentrixMock:
    """
    Stub that simulates read/write operations against a Dentrix patient chart.
    Persists state as JSON files under data/mock_charts/.
    """

    def __init__(self, charts_dir: Path | None = None) -> None:
        self._dir = charts_dir or (MOCK_CASES_DIR.parent / "mock_charts")
        self._dir.mkdir(parents=True, exist_ok=True)

    def _chart_path(self, patient_id: str) -> Path:
        return self._dir / f"{patient_id}.json"

    def get_chart(self, patient_id: str) -> dict:
        path = self._chart_path(patient_id)
        if not path.exists():
            return {"patient_id": patient_id, "teeth": {}, "notes": [], "procedures": []}
        return json.loads(path.read_text())

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

        self._chart_path(patient_id).write_text(json.dumps(chart, indent=2))
        return {"status": "written", "patient_id": patient_id, "entry": entry}

    def get_treatment_plan(self, patient_id: str) -> list[dict]:
        chart = self.get_chart(patient_id)
        return chart.get("proposed_treatment", [])

    def list_patients(self) -> list[str]:
        return [p.stem for p in self._dir.glob("*.json")]
