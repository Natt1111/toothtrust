"""Chart agent: parse voice utterances into structured Dentrix chart entries."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent

_VALID_ENTRY_TYPES = {"finding", "procedure", "note", "medication", "vitals"}
_VALID_CONFIDENCE  = {"high", "medium", "low"}

_SYSTEM = """You are a dental charting assistant.
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
Use standard dental notation. Surface abbreviations: M=mesial, D=distal, O=occlusal, B=buccal, L=lingual, F=facial.

Anti-hallucination rules:
- Only chart findings explicitly stated in the utterance. Do not infer or add clinical findings.
- CDT codes must follow D#### format. If you are unsure of the correct code, leave cdt_code null.
- entry_type must be one of the five allowed values; do not invent new types.
- If the utterance is ambiguous, set confidence to "low" and describe it as a note."""


class ChartAgent(BaseAgent):
    system_prompt = _SYSTEM

    def run(self, utterance: str, session=None, **kwargs) -> dict:
        raw = self._call(utterance)
        try:
            entry = self._parse_json_response(raw)
        except ValueError:
            entry = {
                "entry_type": "note",
                "description": utterance,
                "raw_utterance": utterance,
                "confidence": "low",
            }

        warnings = _validate_chart_entry(entry)
        entry["validation_warnings"] = warnings

        if session is not None:
            session.chart_entries.append(entry)

        return {
            "intent": "chart",
            "entry": entry,
            "validation_warnings": warnings,
            "response": f"Charted: {entry.get('description', utterance)}",
        }


def _validate_chart_entry(entry: dict) -> list[str]:
    """Return validation warnings for a chart entry dict."""
    warnings: list[str] = []

    entry_type = entry.get("entry_type", "")
    if entry_type and entry_type not in _VALID_ENTRY_TYPES:
        warnings.append(
            f"entry_type '{entry_type}' is not in the allowed set {_VALID_ENTRY_TYPES}."
        )

    cdt = entry.get("cdt_code") or ""
    if cdt and not BaseAgent._validate_cdt_format(cdt):
        warnings.append(
            f"cdt_code '{cdt}' does not match the required D#### format."
        )

    conf = entry.get("confidence", "")
    if conf and conf not in _VALID_CONFIDENCE:
        warnings.append(
            f"confidence '{conf}' is not in the allowed set {_VALID_CONFIDENCE}."
        )

    return warnings
