"""Treatment Coordinator Agent: converts clinical audit results into patient-conversation scripts.

Designed for treatment coordinators without clinical training. Output is plain-language,
never clinical jargon, and structured to walk a patient through their options in a way
that builds trust rather than pressure.
"""

from __future__ import annotations

import json

from src.agents.base_agent import BaseAgent

_TC_SYSTEM = """You are a patient communication expert for a dental practice.
Your job is to turn a clinical audit result into a clear, empathetic patient-conversation script
for the treatment coordinator to use. The TC does not have clinical training, so every explanation
must be in plain, everyday language — no CDT codes, no Latin, no clinical abbreviations.

Output ONLY valid JSON in this exact schema:
{
  "opening": "<1-2 sentence warm framing — acknowledge the patient's concern, set the stage>",
  "options": [
    {
      "label": "<Option A: short name>",
      "plain_language": "<what this option involves, in 2-3 sentences a 10th grader would understand>",
      "typical_outcome": "<what usually happens if this works — with a success rate if available>",
      "worst_case": "<honest worst-case scenario in plain language>",
      "timeline": "<how many visits, over how many weeks/months>",
      "estimated_cost": <number in USD>,
      "note": "<optional: any important caveat or insurance consideration>"
    }
  ],
  "recommendation_framing": "<how to present the dentist's recommendation without hard-selling — frame it as the doctor's preference while honoring patient autonomy>",
  "follow_up_questions_to_anticipate": ["<question>", "<question>"],
  "documentation_note": "<what the TC should log about this conversation for the chart>"
}

Rules:
- Never use the words: periapical, radiolucency, obturation, endodontic, osseointegration, CAL, BOP, CDT.
- Never guarantee outcomes. Use phrases like "in most cases", "typically", "the evidence shows".
- Always present at least two options unless the audit result has only one viable path.
- The recommendation framing must honor the patient's right to choose. No pressure language."""


class TreatmentCoordinatorAgent(BaseAgent):
    """Converts an AuditAgent result into a structured patient-conversation script.

    Input: audit result object or dict + optional patient_name and patient_context.
    Output: dict with 'script' key containing the structured conversation guide.
    """

    system_prompt = _TC_SYSTEM
    max_tokens = 2048

    def run(
        self,
        utterance: str = "",
        session=None,
        audit_result=None,
        patient_name: str = "",
        patient_context: str = "",
        **kwargs,
    ) -> dict:
        if audit_result is None and session is not None:
            audit_result = session.audit_result

        if audit_result is None and utterance:
            audit_summary = utterance
        elif audit_result is not None:
            audit_summary = self._format_audit_for_prompt(audit_result)
        else:
            return {
                "intent": "treatment_coordinator",
                "response": "No audit result available. Run an audit first.",
                "script": None,
            }

        prompt_parts = [f"Audit result:\n{audit_summary}"]
        if patient_name:
            prompt_parts.append(f"Patient name: {patient_name}")
        if patient_context:
            prompt_parts.append(f"Additional context: {patient_context}")

        raw = self._call("\n\n".join(prompt_parts))

        try:
            script = json.loads(raw)
        except json.JSONDecodeError:
            script = {"opening": raw, "options": [], "recommendation_framing": "", "follow_up_questions_to_anticipate": [], "documentation_note": ""}

        response_preview = script.get("opening", "Patient conversation script ready.")

        return {
            "intent": "treatment_coordinator",
            "response": response_preview,
            "script": script,
            "patient_name": patient_name,
        }

    @staticmethod
    def _format_audit_for_prompt(audit_result) -> str:
        if isinstance(audit_result, dict):
            return json.dumps(audit_result, indent=2)
        attrs = {}
        for field in ("overall_assessment", "confidence", "findings", "recommendations", "citations"):
            val = getattr(audit_result, field, None)
            if val is not None:
                attrs[field] = val
        return json.dumps(attrs, indent=2) if attrs else str(audit_result)
