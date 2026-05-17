"""Documentation agent: generate patient-facing reports and visit summaries."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.report import to_html, to_text

_DOC_SYSTEM = """You are a patient communication specialist for a dental practice.
Generate clear, empathetic, plain-language documentation from clinical information.
Avoid jargon. Use second person ("your tooth", "your treatment").
Always include a disclaimer that the document is informational and the patient should
discuss all decisions with their dentist."""


class DocumentationAgent(BaseAgent):
    system_prompt = _DOC_SYSTEM
    max_tokens = 1024

    def run(self, utterance: str, session=None, format: str = "text", **kwargs) -> dict:
        if session and session.audit_result:
            if format == "html":
                doc = to_html(session.audit_result)
            else:
                doc = to_text(session.audit_result)
            response = f"Report generated ({len(doc)} chars)."
        else:
            doc = self._call(utterance)
            response = doc

        return {
            "intent": "document",
            "response": response,
            "document": doc,
            "format": format,
        }
