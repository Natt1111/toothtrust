"""Tests for PerioChartAgent — probe parsing, AAP staging, and orchestrator routing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.perio_chart_agent import (
    PerioChartAgent,
    _aap_stage_grade,
    _parse_transcript,
)
from src.orchestrator import Intent, Orchestrator, Session

# Case 3 transcript from data/mock_cases/case_03_perio_voice/voice_transcript.txt
_CASE3_TRANSCRIPT = """\
Tooth 3, distobuccal 4, buccal 3, mesiobuccal 5, bleeding mesial
Tooth 4, distobuccal 3, buccal 2, mesiobuccal 4, no bleeding
Tooth 5, distobuccal 3, buccal 3, mesiobuccal 3, no bleeding
Tooth 12, distobuccal 4, buccal 3, mesiobuccal 5, bleeding mesial
Tooth 13, distolingual 4, lingual 3, mesiolingual 4, distobuccal 4, buccal 3, mesiobuccal 5, bleeding mesiobuccal
Tooth 14, distolingual 3, lingual 2, mesiolingual 3, distobuccal 3, buccal 2, mesiobuccal 4, no bleeding
"""


# ---------------------------------------------------------------------------
# Probe parsing tests (no API calls)
# ---------------------------------------------------------------------------

def test_parse_transcript_returns_correct_tooth_count():
    teeth = _parse_transcript(_CASE3_TRANSCRIPT)
    assert len(teeth) == 6


def test_parse_transcript_tooth_3_depths():
    teeth = _parse_transcript(_CASE3_TRANSCRIPT)
    tooth3 = next(t for t in teeth if t["tooth"] == 3)
    assert tooth3["sites"]["distobuccal"] == 4
    assert tooth3["sites"]["buccal"] == 3
    assert tooth3["sites"]["mesiobuccal"] == 5
    assert tooth3["worst_depth"] == 5


def test_parse_transcript_bleeding_detected():
    teeth = _parse_transcript(_CASE3_TRANSCRIPT)
    tooth3 = next(t for t in teeth if t["tooth"] == 3)
    assert len(tooth3["bleeding_sites"]) >= 1


def test_parse_transcript_no_bleeding_tooth_4():
    teeth = _parse_transcript(_CASE3_TRANSCRIPT)
    tooth4 = next(t for t in teeth if t["tooth"] == 4)
    assert tooth4["bleeding_sites"] == []


def test_parse_transcript_tooth_13_full_sites():
    teeth = _parse_transcript(_CASE3_TRANSCRIPT)
    tooth13 = next(t for t in teeth if t["tooth"] == 13)
    # Tooth 13 has both buccal and lingual sites
    assert "distobuccal" in tooth13["sites"]
    assert "distolingual" in tooth13["sites"]
    assert tooth13["worst_depth"] == 5


# ---------------------------------------------------------------------------
# AAP staging tests (no API calls)
# ---------------------------------------------------------------------------

def test_aap_stage_1_for_shallow_pockets():
    stage, grade = _aap_stage_grade(2)
    assert stage == "Stage I"
    assert grade == "Grade B"


def test_aap_stage_2_for_moderate_pockets():
    stage, grade = _aap_stage_grade(4)
    assert stage == "Stage II"


def test_aap_stage_3_for_deep_pockets():
    stage, grade = _aap_stage_grade(5)
    assert stage == "Stage III"


# ---------------------------------------------------------------------------
# Full agent run tests (mocked API for recommendations)
# ---------------------------------------------------------------------------

@patch("src.agents.base_agent._client")
def test_perio_chart_agent_case3_full_run(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Continue 4-month maintenance. Reinforce hygiene at teeth 3, 12, 13.")]
    )
    agent = PerioChartAgent()
    result = agent.run(transcript=_CASE3_TRANSCRIPT)

    assert result["intent"] == "perio_chart"
    assert result["chart"] is not None
    assert result["chart"]["summary"]["teeth_charted"] == 6
    assert result["chart"]["summary"]["aap_stage"] in ("Stage I", "Stage II", "Stage III")
    assert result["chart"]["summary"]["worst_cal"] == 5


@patch("src.agents.base_agent._client")
def test_perio_chart_agent_stores_chart_in_session(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Monitor and maintain.")]
    )
    session = Session(session_id="s1", patient_id="p47")
    agent = PerioChartAgent()
    agent.run(transcript=_CASE3_TRANSCRIPT, session=session)

    assert session.perio_chart is not None
    assert len(session.perio_chart["teeth"]) == 6


@patch("src.agents.base_agent._client")
def test_perio_chart_agent_empty_transcript(mock_client):
    agent = PerioChartAgent()
    result = agent.run(transcript="   ")

    assert result["intent"] == "perio_chart"
    assert result["chart"] is None
    assert "No probe data" in result["response"]


@patch("src.agents.base_agent._client")
def test_perio_chart_agent_simple_single_tooth(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Within normal limits.")]
    )
    agent = PerioChartAgent()
    result = agent.run(transcript="Tooth 7, distobuccal 2, buccal 2, mesiobuccal 2, no bleeding")

    assert result["chart"]["summary"]["teeth_charted"] == 1
    assert result["chart"]["summary"]["aap_stage"] == "Stage I"


# ---------------------------------------------------------------------------
# Orchestrator routing tests
# ---------------------------------------------------------------------------

def test_orchestrator_routes_perio_pattern_without_llm():
    """Perio probe patterns should be caught by regex fast-path, no LLM call."""
    orch = Orchestrator()
    intent = orch.classify_intent("Tooth 3, distobuccal 4, buccal 3, mesiobuccal 5, bleeding mesial")
    assert intent == Intent.PERIO_CHART


@patch("src.orchestrator._client")
def test_orchestrator_routes_perio_chart_intent_from_llm(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="perio_chart")]
    )
    orch = Orchestrator()
    intent = orch.classify_intent("start perio chart")
    assert intent == Intent.PERIO_CHART
