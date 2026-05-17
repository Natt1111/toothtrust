"""Tests for the agent layer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.chart_agent import ChartAgent
from src.agents.research_agent import ResearchAgent
from src.orchestrator import Intent, Orchestrator, Session


# ─── ChartAgent ────────────────────────────────────────────────────────────────

MOCK_CHART_JSON = """{
  "entry_type": "procedure",
  "tooth": 19,
  "surface": "MOD",
  "cdt_code": "D2150",
  "description": "Amalgam restoration, MOD, tooth 19",
  "raw_utterance": "chart MOD amalgam on 19",
  "confidence": "high"
}"""


@patch("src.agents.base_agent._client")
def test_chart_agent_parses_utterance(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_CHART_JSON)]
    )
    agent = ChartAgent()
    result = agent.run(utterance="chart MOD amalgam on 19")

    assert result["intent"] == "chart"
    assert result["entry"]["tooth"] == 19
    assert result["entry"]["cdt_code"] == "D2150"


@patch("src.agents.base_agent._client")
def test_chart_agent_appends_to_session(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=MOCK_CHART_JSON)]
    )
    session = Session(session_id="test", patient_id="p001")
    agent = ChartAgent()
    agent.run(utterance="chart MOD amalgam on 19", session=session)

    assert len(session.chart_entries) == 1
    assert session.chart_entries[0]["tooth"] == 19


@patch("src.agents.base_agent._client")
def test_chart_agent_handles_bad_json(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="not json")]
    )
    agent = ChartAgent()
    result = agent.run(utterance="some utterance")

    assert result["intent"] == "chart"
    assert result["entry"]["confidence"] == "low"


# ─── ResearchAgent ─────────────────────────────────────────────────────────────

@patch("src.agents.research_agent._retriever")
@patch("src.agents.base_agent._client")
def test_research_agent_returns_answer(mock_client, mock_retriever):
    mock_retriever.retrieve.return_value = [{"source": "ADA.pdf", "text": "Evidence..."}]
    mock_retriever.format_context.return_value = "[1] Source: ADA.pdf\nEvidence..."
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Bisphosphonates increase MRONJ risk. Source: ADA.pdf.")]
    )

    agent = ResearchAgent()
    result = agent.run(utterance="bisphosphonate contraindications for extraction")

    assert result["intent"] == "research"
    assert "bisphosphonate" in result["response"].lower() or len(result["response"]) > 10
    assert "ADA.pdf" in result["sources"]


# ─── Orchestrator ──────────────────────────────────────────────────────────────

@patch("src.orchestrator._client")
def test_orchestrator_classify_chart(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="chart")]
    )
    orch = Orchestrator()
    intent = orch.classify_intent("chart MOD on 19")
    assert intent == Intent.CHART


@patch("src.orchestrator._client")
def test_orchestrator_classify_research(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="research")]
    )
    orch = Orchestrator()
    intent = orch.classify_intent("what is the evidence for fluoride varnish?")
    assert intent == Intent.RESEARCH


@patch("src.orchestrator._client")
def test_orchestrator_unknown_intent(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="gibberish")]
    )
    orch = Orchestrator()
    intent = orch.classify_intent("blah blah")
    assert intent == Intent.UNKNOWN
