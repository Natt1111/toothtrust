"""Tests for TreatmentCoordinatorAgent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.agents.treatment_coordinator_agent import TreatmentCoordinatorAgent
from src.orchestrator import Intent, Orchestrator, Session

_MOCK_SCRIPT = json.dumps({
    "opening": "Dr. Patel found a cavity on tooth 19 and wants to go over your options.",
    "options": [
        {
            "label": "Option A: Tooth-colored filling",
            "plain_language": "We remove the decay and fill the space with a white material that matches your tooth.",
            "typical_outcome": "Lasts 7-10 years with good oral hygiene.",
            "worst_case": "If the decay is deeper than expected, you may need a crown instead.",
            "timeline": "One visit, about 45 minutes.",
            "estimated_cost": 220,
            "note": ""
        }
    ],
    "recommendation_framing": "Dr. Patel recommends the filling as the most conservative option right now.",
    "follow_up_questions_to_anticipate": ["Will it hurt?", "How long will it last?"],
    "documentation_note": "Patient presented with options for tooth 19 caries. Filling recommended."
})


@patch("src.agents.base_agent._client")
def test_tc_agent_returns_script_from_audit_result(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=_MOCK_SCRIPT)]
    )
    audit_result = {
        "overall_assessment": "LIKELY OVERTREATMENT",
        "recommendations": "Use D2391 composite instead of D2750 crown.",
    }
    agent = TreatmentCoordinatorAgent()
    result = agent.run(audit_result=audit_result, patient_name="James")

    assert result["intent"] == "treatment_coordinator"
    assert result["script"] is not None
    assert "options" in result["script"]
    assert len(result["script"]["options"]) >= 1
    assert result["patient_name"] == "James"


@patch("src.agents.base_agent._client")
def test_tc_agent_uses_session_audit_result(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=_MOCK_SCRIPT)]
    )
    session = Session(session_id="s1", patient_id="p42")
    session.audit_result = {
        "overall_assessment": "QUESTIONABLE",
        "recommendations": "Present endo option before implant.",
    }
    agent = TreatmentCoordinatorAgent()
    result = agent.run(session=session)

    assert result["intent"] == "treatment_coordinator"
    assert result["script"]["opening"] is not None


@patch("src.agents.base_agent._client")
def test_tc_agent_handles_missing_audit_gracefully(mock_client):
    agent = TreatmentCoordinatorAgent()
    result = agent.run(utterance="", session=None, audit_result=None)

    assert result["intent"] == "treatment_coordinator"
    assert result["script"] is None
    assert "audit" in result["response"].lower()


@patch("src.agents.base_agent._client")
def test_tc_agent_handles_bad_json_from_llm(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Sorry, I cannot process this.")]
    )
    agent = TreatmentCoordinatorAgent()
    result = agent.run(audit_result={"overall_assessment": "OVERTREATMENT"})

    assert result["intent"] == "treatment_coordinator"
    assert result["script"] is not None
    # Bad JSON falls back to raw text in opening field
    assert isinstance(result["script"].get("opening"), str)


@patch("src.orchestrator._client")
def test_orchestrator_routes_tc_intent(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="treatment_coordinator")]
    )
    orch = Orchestrator()
    intent = orch.classify_intent("explain this treatment plan to the patient")
    assert intent == Intent.TREATMENT_COORDINATOR
