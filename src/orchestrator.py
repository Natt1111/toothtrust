"""Session orchestrator: routes intents from voice or API to the appropriate agent."""

from __future__ import annotations

import re
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
    TREATMENT_COORDINATOR = "treatment_coordinator"
    PERIO_CHART = "perio_chart"
    LAB_CASE = "lab_case"
    UNKNOWN = "unknown"


_ROUTER_SYSTEM = """You are an intent classifier for a dental clinical assistant.
Classify the user utterance into one of: chart, audit, research, document, treatment_coordinator, perio_chart, lab_case, unknown.

- chart: recording a clinical finding, note, or procedure (e.g. "chart MOD on 19", "note: patient reports sensitivity")
- audit: evaluating or reviewing a treatment plan (e.g. "audit this plan", "is this crown justified?")
- research: answering a clinical question (e.g. "what are the contraindications for bisphosphonates before extraction?")
- document: generating or reviewing a clinical SOAP note (e.g. "draft the note", "sign it", "read me the note")
- treatment_coordinator: generating a patient-conversation script from an audit (e.g. "explain this to the patient", "create a treatment coordinator script", "help me present this plan")
- perio_chart: recording periodontal probe depths from a voice transcript (e.g. "tooth 3 distobuccal 4 buccal 3", "perio chart", "start probe recording")
- lab_case: any lab case status query or action (e.g. "scan tomorrow's lab cases", "where's the Chen case", "mark the Johnson case received", "lab cases at risk", "where did it fall through")
- unknown: anything else

Respond with ONLY the intent word, lowercase."""

# Regex for detecting perio probe depth patterns directly (bypasses LLM classification for speed)
_PERIO_PATTERN = re.compile(
    r"\btooth\s+\d+.*\b(distobuccal|mesiobuccal|buccal|distolingual|mesiolingual|lingual|\bdb\b|\bmb\b)\s+\d+",
    re.IGNORECASE,
)

# Regex fast-path for common lab case queries (bypasses LLM for speed)
_LAB_CASE_PATTERN = re.compile(
    r"\b(scan\s+(tomorrow|lab)|where.{0,25}case|lab\s+case[s]?\s+(at\s+risk|scan|status)|"
    r"mark\s+\w+\s+(case\s+)?received|check\s+(in\s+)?the\s+\w+\s+case|"
    r"where.{0,20}fall\s+through|lab\s+cases?\b)\b",
    re.IGNORECASE,
)


@dataclass
class Session:
    session_id: str
    patient_id: str = ""
    history: list[dict] = field(default_factory=list)
    chart_entries: list[dict] = field(default_factory=list)
    audit_result: object = None
    documentation_draft: dict | None = None
    perio_chart: dict | None = None


class Orchestrator:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create_session(self, session_id: str, patient_id: str = "") -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id, patient_id=patient_id)
        return self._sessions[session_id]

    def classify_intent(self, utterance: str) -> Intent:
        # Fast-path: detect perio probe calls by pattern before calling the LLM
        if _PERIO_PATTERN.search(utterance):
            return Intent.PERIO_CHART
        # Fast-path: detect lab case queries by pattern before calling the LLM
        if _LAB_CASE_PATTERN.search(utterance):
            return Intent.LAB_CASE

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
        from src.agents.lab_case_agent import LabCaseAgent
        from src.agents.perio_chart_agent import PerioChartAgent
        from src.agents.research_agent import ResearchAgent
        from src.agents.treatment_coordinator_agent import TreatmentCoordinatorAgent

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
        elif intent == Intent.TREATMENT_COORDINATOR:
            agent = TreatmentCoordinatorAgent()
            result = agent.run(utterance=utterance, session=session, **kwargs)
        elif intent == Intent.PERIO_CHART:
            agent = PerioChartAgent()
            result = agent.run(utterance=utterance, session=session, **kwargs)
        elif intent == Intent.LAB_CASE:
            agent = LabCaseAgent()
            result = agent.run(utterance=utterance, session=session, **kwargs)
        else:
            result = {"intent": "unknown", "response": "I didn't understand that. Try again."}

        session.history.append({"utterance": utterance, "intent": intent, "result": result})
        return result
