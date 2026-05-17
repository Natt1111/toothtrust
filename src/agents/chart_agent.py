"""Chart agent: parse voice utterances into structured Dentrix chart entries."""

from __future__ import annotations

import json

from src.agents.base_agent import BaseAgent


class ChartAgent(BaseAgent):
    system_prompt = """You are a dental charting assistant.
Parse the clinician's voice utterance into a structured chart entry.
Return ONLY valid JSON:
{
  "entry_type": "finding|procedure|note|medication|vitals",
  "tooth": <number or null>,
  "surface": "<MO/DO/MOD/etc or null>",
  "cdt_code": "<D-code or null>",
  "description": "<normalized description>",
  "raw_utterance": "<original text>",
  "confidence": "high|medium|low"
}
Use standard dental notation. Surface abbreviations: M=mesial, D=distal, O=occlusal, B=buccal, L=lingual, F=facial."""

    def run(self, utterance: str, session=None, **kwargs) -> dict:
        raw = self._call(utterance)
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            entry = {"entry_type": "note", "description": utterance, "raw_utterance": utterance, "confidence": "low"}

        if session is not None:
            session.chart_entries.append(entry)

        return {"intent": "chart", "entry": entry, "response": f"Charted: {entry.get('description', utterance)}"}
