"""Session orchestrator: routes intents from voice or API to the appropriate agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


class Intent(str, Enum):
    CHART = "chart"
    AUDIT = "audit"
    RESEARCH = "research"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


_ROUTER_SYSTEM = """You are an intent classifier for a dental clinical assistant.
Classify the user utterance into one of: chart, audit, research, document, unknown.

- chart: recording a clinical finding, note, or procedure (e.g. "chart MOD on 19", "note: patient reports sensitivity")
- audit: evaluating or reviewing a treatment plan (e.g. "audit this plan", "is this crown justified?")
- research: answering a clinical question (e.g. "what are the contraindications for bisphosphonates before extraction?")
- document: generating a patient report or summary (e.g. "create the patient report", "summarize today's visit")
- unknown: anything else

Respond with ONLY the intent word, lowercase."""


@dataclass
class Session:
    session_id: str
    patient_id: str = ""
    history: list[dict] = field(default_factory=list)
    chart_entries: list[dict] = field(default_factory=list)
    audit_result: object = None


class Orchestrator:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create_session(self, session_id: str, patient_id: str = "") -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id, patient_id=patient_id)
        return self._sessions[session_id]

    def classify_intent(self, utterance: str) -> Intent:
        response = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16,
            system=_ROUTER_SYSTEM,
            messages=[{"role": "user", "content": utterance}],
        )
        raw = response.content[0].text.strip().lower()
        try:
            return Intent(raw)
        except ValueError:
            return Intent.UNKNOWN

    def route(self, session_id: str, utterance: str, **kwargs) -> dict:
        """Classify utterance and dispatch to the appropriate agent. Returns agent response dict."""
        from src.agents.audit_agent import AuditAgent
        from src.agents.chart_agent import ChartAgent
        from src.agents.documentation_agent import DocumentationAgent
        from src.agents.research_agent import ResearchAgent

        session = self.get_or_create_session(session_id)
        intent = self.classify_intent(utterance)

        if intent == Intent.CHART:
            agent = ChartAgent()
            result = agent.run(utterance=utterance, session=session, **kwargs)
        elif intent == Intent.AUDIT:
            agent = AuditAgent()
            result = agent.run(utterance=utterance, session=session, **kwargs)
        elif intent == Intent.RESEARCH:
            agent = ResearchAgent()
            result = agent.run(utterance=utterance, session=session, **kwargs)
        elif intent == Intent.DOCUMENT:
            agent = DocumentationAgent()
            result = agent.run(utterance=utterance, session=session, **kwargs)
        else:
            result = {"intent": "unknown", "response": "I didn't understand that. Try again."}

        session.history.append({"utterance": utterance, "intent": intent, "result": result})
        return result
