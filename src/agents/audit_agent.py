"""Audit agent: run a treatment plan audit from a voice or API request."""

from __future__ import annotations

import json

from src.agents.base_agent import BaseAgent
from src.audit import audit_treatment_plan
from src.report import to_text


class AuditAgent(BaseAgent):
    system_prompt = """You are a dental treatment plan coordinator.
Extract a structured treatment plan from the user's request.
Return ONLY valid JSON — a list of procedures:
[{"cdt_code": "<code or empty>", "description": "<procedure>", "tooth": <number or null>}]
If the user pastes a plan, parse it. If they describe it verbally, structure it."""

    def run(self, utterance: str, session=None, treatment_plan: list | None = None, patient_context: str = "", **kwargs) -> dict:
        if treatment_plan is None:
            raw = self._call(utterance)
            try:
                treatment_plan = json.loads(raw)
            except json.JSONDecodeError:
                treatment_plan = [{"cdt_code": "", "description": utterance, "tooth": None}]

        result = audit_treatment_plan(treatment_plan, patient_context=patient_context)

        if session is not None:
            session.audit_result = result

        return {
            "intent": "audit",
            "overall": result.overall_assessment,
            "confidence": result.confidence,
            "response": to_text(result),
            "audit_result": result,
        }
