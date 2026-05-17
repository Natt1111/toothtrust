"""Mock Videa/X-ray integration — returns synthetic radiograph analysis results."""

from __future__ import annotations

import random
from pathlib import Path


_SYNTHETIC_CONDITIONS = [
    "interproximal caries - early",
    "interproximal caries - moderate",
    "recurrent caries under existing restoration",
    "widened periodontal ligament space",
    "periapical radiolucency",
    "bone loss - horizontal pattern",
    "bone loss - vertical pattern",
    "calculus deposits",
    "root resorption",
]

_SYNTHETIC_HEALTHY = [
    "within normal limits",
    "no significant radiographic findings",
    "intact lamina dura",
    "normal bone height",
]


class VideaMock:
    """
    Stub that returns synthetic X-ray analysis results.
    In production, replace with the Videa AI API or equivalent.
    """

    def analyze(self, image_path: Path | str, patient_id: str = "") -> dict:
        """Return synthetic AI-generated radiograph findings."""
        path = Path(image_path)
        tooth_count = random.randint(4, 8)
        teeth: dict[str, dict] = {}

        for _ in range(tooth_count):
            tooth_num = random.randint(1, 32)
            if random.random() > 0.4:
                conditions = random.sample(_SYNTHETIC_CONDITIONS, k=random.randint(1, 2))
            else:
                conditions = [random.choice(_SYNTHETIC_HEALTHY)]
            teeth[str(tooth_num)] = {"conditions": conditions}

        return {
            "source": path.name,
            "patient_id": patient_id,
            "model": "videa-mock-v1",
            "teeth": teeth,
            "overall_bone_level": random.choice(["normal", "mild loss", "moderate loss"]),
            "confidence": random.choice(["high", "medium"]),
            "note": "SYNTHETIC DATA — not for clinical use",
        }
