"""Perio Chart Agent: converts hygienist voice probe calls into a structured periodontal chart
with AAP 2017 staging and grading.

Probe parsing is done locally via regex for reliability and testability. Claude is called only
for the narrative recommendations section, which benefits from contextual judgment.

Expected transcript format per tooth:
  "Tooth [#], [site] [depth], [site] [depth], ..., [bleeding/recession note]"

Supported sites: distobuccal, buccal, mesiobuccal, distolingual, lingual, mesiolingual
"""

from __future__ import annotations

import json
import re

from src.agents.base_agent import BaseAgent

_SITE_ALIASES: dict[str, str] = {
    "db": "distobuccal",
    "b": "buccal",
    "mb": "mesiobuccal",
    "dl": "distolingual",
    "l": "lingual",
    "ml": "mesiolingual",
    "distobuccal": "distobuccal",
    "buccal": "buccal",
    "mesiobuccal": "mesiobuccal",
    "distolingual": "distolingual",
    "lingual": "lingual",
    "mesiolingual": "mesiolingual",
}

_TOOTH_LINE_RE = re.compile(
    r"tooth\s+(\d+)[,\s]+(.*)",
    re.IGNORECASE,
)
_SITE_DEPTH_RE = re.compile(
    r"(distobuccal|mesiobuccal|buccal|distolingual|mesiolingual|lingual|db|mb|b|dl|ml|l)\s+(\d+)",
    re.IGNORECASE,
)
_BLEEDING_RE = re.compile(
    r"bleeding\s+([\w]+)",
    re.IGNORECASE,
)

_RECS_SYSTEM = """You are a dental hygiene clinical advisor.
Given a structured periodontal chart summary with AAP 2017 stage and grade, write 2-4 concise
sentences of recommended next steps for the hygienist and dentist. Be specific — reference the
teeth with the deepest pockets and the bleeding sites. Use evidence-based language."""


class PerioChartAgent(BaseAgent):
    """Converts a voice probe transcript into a structured periodontal chart.

    Probe parsing is local (deterministic). AAP staging is computed from worst CAL proxy.
    Claude generates the narrative recommendations only.
    """

    system_prompt = _RECS_SYSTEM
    max_tokens = 512

    def run(
        self,
        utterance: str = "",
        session=None,
        transcript: str | None = None,
        corpus_citations: list[str] | None = None,
        **kwargs,
    ) -> dict:
        text = transcript if transcript is not None else utterance
        teeth = _parse_transcript(text)

        if not teeth:
            return {
                "intent": "perio_chart",
                "response": "No probe data found in transcript. Check format.",
                "chart": None,
            }

        summary = _compute_summary(teeth)
        stage, grade = _aap_stage_grade(summary["worst_cal"])
        summary["aap_stage"] = stage
        summary["aap_grade"] = grade

        prompt = (
            f"Periodontal chart summary:\n{json.dumps(summary, indent=2)}\n\n"
            f"Patient history: perio maintenance patient.\n"
            f"Provide recommended next steps."
        )
        recommendations = self._call(prompt, system=_RECS_SYSTEM)
        summary["recommended_next_steps"] = recommendations

        if corpus_citations:
            summary["citations"] = corpus_citations

        chart = {"teeth": teeth, "summary": summary}

        if session is not None:
            session.perio_chart = chart

        response = (
            f"Charted {summary['teeth_charted']} teeth. "
            f"Worst pocket: {summary['worst_cal']}mm. "
            f"AAP {stage}, {grade}. "
            f"BOP: {summary['bop_percent']:.0f}%."
        )

        return {"intent": "perio_chart", "response": response, "chart": chart}


# ---------------------------------------------------------------------------
# Local parsing helpers
# ---------------------------------------------------------------------------

def _parse_transcript(text: str) -> list[dict]:
    teeth = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = _TOOTH_LINE_RE.match(line)
        if not m:
            continue
        tooth_num = int(m.group(1))
        rest = m.group(2)

        sites: dict[str, int] = {}
        for sm in _SITE_DEPTH_RE.finditer(rest):
            site_raw = sm.group(1).lower()
            depth = int(sm.group(2))
            site = _SITE_ALIASES.get(site_raw, site_raw)
            sites[site] = depth

        bleeding_sites: list[str] = []
        for bm in _BLEEDING_RE.finditer(rest):
            location = bm.group(1).lower()
            site = _SITE_ALIASES.get(location, location)
            bleeding_sites.append(site)

        if not sites:
            continue

        worst = max(sites.values())
        teeth.append({
            "tooth": tooth_num,
            "sites": sites,
            "bleeding_sites": bleeding_sites,
            "recession": {},
            "worst_depth": worst,
            "cal_proxy": worst,
        })
    return teeth


def _compute_summary(teeth: list[dict]) -> dict:
    all_depths = [d for t in teeth for d in t["sites"].values()]
    total_sites = len(all_depths)
    bleeding_count = sum(len(t["bleeding_sites"]) for t in teeth)
    worst_cal = max(t["cal_proxy"] for t in teeth) if teeth else 0
    bop_pct = round(bleeding_count / total_sites * 100, 1) if total_sites else 0.0
    return {
        "teeth_charted": len(teeth),
        "total_sites": total_sites,
        "bleeding_on_probing_sites": bleeding_count,
        "bop_percent": bop_pct,
        "worst_cal": worst_cal,
        "aap_stage": "",
        "aap_grade": "",
        "staging_rationale": "",
        "grading_rationale": "",
        "recommended_next_steps": "",
    }


def _aap_stage_grade(worst_cal: int) -> tuple[str, str]:
    """Heuristic AAP 2017 stage from worst CAL proxy (probe depth as surrogate).

    Stage I:   CAL 1–2mm
    Stage II:  CAL 3–4mm
    Stage III: CAL ≥5mm (no complexity factors → could be IV, but v1 stops at III)
    Grade B:   default in v1 (no radiographic bone loss rate or systemic risk data from transcript)
    """
    if worst_cal <= 2:
        stage = "Stage I"
    elif worst_cal <= 4:
        stage = "Stage II"
    else:
        stage = "Stage III"
    return stage, "Grade B"
