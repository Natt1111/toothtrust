"""Anti-hallucination guard tests for all 7 ToothTrust agents.

These tests verify that each agent:
- Validates CDT code format correctly
- Catches citations not present in the retrieved context
- Detects AI-speaker preamble patterns
- Validates output schema fields (entry_type, options, SOAP fields, etc.)
- Has explicit anti-hallucination language in its system prompt

All tests are unit tests — no Claude API calls are made (clients are patched).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.base_agent import BaseAgent
from src.agents.chart_agent import ChartAgent, _validate_chart_entry
from src.agents.documentation_agent import DocumentationAgent, _validate_soap_note
from src.agents.treatment_coordinator_agent import TreatmentCoordinatorAgent, _validate_tc_script
from src.audit import AuditResult, _validate_audit_output


# ── BaseAgent helpers ─────────────────────────────────────────────────────────

class TestValidateCdtFormat:
    def test_valid_d2750(self):
        assert BaseAgent._validate_cdt_format("D2750") is True

    def test_valid_d0150(self):
        assert BaseAgent._validate_cdt_format("D0150") is True

    def test_valid_d8090(self):
        assert BaseAgent._validate_cdt_format("D8090") is True

    def test_invalid_too_short(self):
        assert BaseAgent._validate_cdt_format("D275") is False

    def test_invalid_too_long(self):
        assert BaseAgent._validate_cdt_format("D27500") is False

    def test_invalid_no_d_prefix(self):
        assert BaseAgent._validate_cdt_format("2750") is False

    def test_invalid_letters_in_digits(self):
        assert BaseAgent._validate_cdt_format("D275X") is False

    def test_empty_string(self):
        assert BaseAgent._validate_cdt_format("") is False

    def test_strips_whitespace(self):
        assert BaseAgent._validate_cdt_format("  D2750  ") is True


class TestValidateCitations:
    def test_all_valid_returns_empty(self):
        allowed = {"crown_indications_ada.md", "composite_vs_crown_decision_criteria.md"}
        fabricated = BaseAgent._validate_citations(
            ["crown_indications_ada.md"], allowed
        )
        assert fabricated == []

    def test_fabricated_citation_detected(self):
        allowed = {"crown_indications_ada.md"}
        fabricated = BaseAgent._validate_citations(
            ["crown_indications_ada.md", "made_up_source.pdf"], allowed
        )
        assert "made_up_source.pdf" in fabricated

    def test_empty_citations_returns_empty(self):
        assert BaseAgent._validate_citations([], {"some_source.md"}) == []

    def test_all_fabricated(self):
        result = BaseAgent._validate_citations(
            ["fake1.pdf", "fake2.md"], {"real_source.md"}
        )
        assert len(result) == 2


class TestHasAiPreamble:
    def test_detects_as_an_ai(self):
        assert BaseAgent._has_ai_preamble("As an AI, I cannot provide medical advice.") is True

    def test_detects_i_am_an_ai(self):
        assert BaseAgent._has_ai_preamble("I am an AI language model.") is True

    def test_clean_response_passes(self):
        assert BaseAgent._has_ai_preamble("Crown preparation is indicated when...") is False

    def test_empty_string_passes(self):
        assert BaseAgent._has_ai_preamble("") is False


# ── AuditResult has validation_warnings field ────────────────────────────────

def test_audit_result_has_validation_warnings_field():
    result = AuditResult(
        overall_assessment="supported",
        confidence="high",
        procedures=[],
        missing_information=[],
        patient_summary="",
    )
    assert hasattr(result, "validation_warnings")
    assert isinstance(result.validation_warnings, list)


def test_validate_audit_output_catches_fabricated_citation():
    chunks = [{"source": "crown_indications_ada.md", "text": "..."}]
    data = {
        "overall_assessment": "unsupported",
        "confidence": "high",
        "procedures": [{
            "cdt_code": "D2750",
            "description": "Crown",
            "verdict": "unsupported",
            "rationale": "Not indicated.",
            "flags": [],
            "citations": ["crown_indications_ada.md", "FABRICATED_SOURCE.pdf"],
        }],
    }
    warnings = _validate_audit_output(data, chunks)
    assert any("FABRICATED_SOURCE.pdf" in w for w in warnings)


def test_validate_audit_output_accepts_valid_citations():
    chunks = [
        {"source": "crown_indications_ada.md", "text": "..."},
        {"source": "caries_classification_icdas.md", "text": "..."},
    ]
    data = {
        "overall_assessment": "unsupported",
        "confidence": "high",
        "procedures": [{
            "cdt_code": "D2750",
            "description": "Crown",
            "verdict": "unsupported",
            "rationale": "Not indicated.",
            "flags": [],
            "citations": ["crown_indications_ada.md"],
        }],
    }
    warnings = _validate_audit_output(data, chunks)
    citation_warnings = [w for w in warnings if "cited" in w]
    assert citation_warnings == []


def test_validate_audit_output_catches_invalid_overall_assessment():
    data = {"overall_assessment": "definitely_wrong", "confidence": "high", "procedures": []}
    warnings = _validate_audit_output(data, [])
    assert any("overall_assessment" in w for w in warnings)


def test_validate_audit_output_catches_invalid_confidence():
    data = {"overall_assessment": "supported", "confidence": "absolutely", "procedures": []}
    warnings = _validate_audit_output(data, [])
    assert any("confidence" in w for w in warnings)


def test_validate_audit_output_catches_bad_cdt_in_procedure():
    data = {
        "overall_assessment": "supported",
        "confidence": "high",
        "procedures": [{
            "cdt_code": "NOTACODE",
            "verdict": "supported",
            "citations": [],
        }],
    }
    warnings = _validate_audit_output(data, [])
    assert any("cdt_code" in w for w in warnings)


# ── ChartAgent ────────────────────────────────────────────────────────────────

def test_chart_entry_valid_passes():
    entry = {
        "entry_type": "procedure",
        "cdt_code": "D2750",
        "confidence": "high",
    }
    assert _validate_chart_entry(entry) == []


def test_chart_entry_invalid_entry_type_flagged():
    entry = {"entry_type": "MADE_UP_TYPE", "cdt_code": "D2750", "confidence": "high"}
    warnings = _validate_chart_entry(entry)
    assert any("entry_type" in w for w in warnings)


def test_chart_entry_bad_cdt_flagged():
    entry = {"entry_type": "procedure", "cdt_code": "BADCODE", "confidence": "high"}
    warnings = _validate_chart_entry(entry)
    assert any("cdt_code" in w for w in warnings)


def test_chart_entry_null_cdt_not_flagged():
    entry = {"entry_type": "note", "cdt_code": None, "confidence": "low"}
    assert _validate_chart_entry(entry) == []


def test_chart_entry_invalid_confidence_flagged():
    entry = {"entry_type": "finding", "cdt_code": None, "confidence": "certain"}
    warnings = _validate_chart_entry(entry)
    assert any("confidence" in w for w in warnings)


@patch("src.agents.base_agent._client")
def test_chart_agent_returns_validation_warnings_in_result(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps({
            "entry_type": "procedure",
            "tooth": 19,
            "surface": "MOD",
            "cdt_code": "D2150",
            "description": "Amalgam restoration",
            "raw_utterance": "chart MOD amalgam on 19",
            "confidence": "high",
        }))]
    )
    agent = ChartAgent()
    result = agent.run(utterance="chart MOD amalgam on 19")
    assert "validation_warnings" in result
    assert isinstance(result["validation_warnings"], list)


@patch("src.agents.base_agent._client")
def test_chart_agent_flags_bad_cdt_in_llm_response(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps({
            "entry_type": "procedure",
            "tooth": 19,
            "cdt_code": "BADCODE",
            "description": "Something",
            "raw_utterance": "chart something",
            "confidence": "high",
        }))]
    )
    agent = ChartAgent()
    result = agent.run(utterance="chart something")
    assert any("cdt_code" in w for w in result["validation_warnings"])


# ── ResearchAgent ─────────────────────────────────────────────────────────────

@patch("src.agents.research_agent._retriever")
@patch("src.agents.base_agent._client")
def test_research_agent_returns_validated_sources(mock_client, mock_retriever):
    mock_retriever.retrieve.return_value = [{"source": "crown_indications_ada.md", "text": "Evidence..."}]
    mock_retriever.format_context.return_value = "[1] Source: crown_indications_ada.md\nEvidence..."
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Crown is indicated when structural damage exceeds 50%. Source: crown_indications_ada.md.")]
    )
    from src.agents.research_agent import ResearchAgent
    agent = ResearchAgent()
    result = agent.run(utterance="when is a crown indicated?")
    assert "validated_sources" in result
    assert "crown_indications_ada.md" in result["validated_sources"]


@patch("src.agents.research_agent._retriever")
@patch("src.agents.base_agent._client")
def test_research_agent_flags_ai_preamble(mock_client, mock_retriever):
    mock_retriever.retrieve.return_value = [{"source": "crown_indications_ada.md", "text": "..."}]
    mock_retriever.format_context.return_value = "..."
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="As an AI, I cannot provide medical advice.")]
    )
    from src.agents.research_agent import ResearchAgent
    agent = ResearchAgent()
    result = agent.run(utterance="something")
    assert any("preamble" in w.lower() for w in result["validation_warnings"])


# ── DocumentationAgent ────────────────────────────────────────────────────────

def test_validate_soap_note_all_fields_present():
    note = {
        "subjective": "Patient reports tooth pain.",
        "objective": "Periapical radiograph taken.",
        "assessment": "Caries, tooth #19.",
        "plan": "Composite restoration.",
        "medications": "2% Lidocaine administered.",
        "patient_response": "Tolerated well.",
        "cdt_codes": ["D2391"],
    }
    assert _validate_soap_note(note) == []


def test_validate_soap_note_missing_fields_flagged():
    note = {"subjective": "Pain.", "objective": ""}
    warnings = _validate_soap_note(note)
    assert any("missing fields" in w for w in warnings)


def test_validate_soap_note_bad_cdt_flagged():
    note = {
        "subjective": "", "objective": "", "assessment": "",
        "plan": "", "medications": "", "patient_response": "",
        "cdt_codes": ["BADCODE"],
    }
    warnings = _validate_soap_note(note)
    assert any("BADCODE" in w for w in warnings)


def test_validate_soap_note_valid_cdt_passes():
    note = {
        "subjective": "", "objective": "", "assessment": "",
        "plan": "", "medications": "", "patient_response": "",
        "cdt_codes": ["D2391", "D0150"],
    }
    assert _validate_soap_note(note) == []


# ── TreatmentCoordinatorAgent ─────────────────────────────────────────────────

def test_validate_tc_script_valid_passes():
    script = {
        "opening": "Let's walk through your options.",
        "options": [
            {"label": "Option A", "plain_language": "A filling.", "estimated_cost": 220},
            {"label": "Option B", "plain_language": "A crown.", "estimated_cost": 1400},
        ],
        "recommendation_framing": "Dr. Patel recommends Option A.",
        "follow_up_questions_to_anticipate": [],
        "documentation_note": "TC reviewed options.",
    }
    assert _validate_tc_script(script) == []


def test_validate_tc_script_empty_options_flagged():
    script = {"options": []}
    warnings = _validate_tc_script(script)
    assert any("options" in w for w in warnings)


def test_validate_tc_script_missing_options_flagged():
    script = {"opening": "Hello."}
    warnings = _validate_tc_script(script)
    assert any("options" in w for w in warnings)


def test_validate_tc_script_non_numeric_cost_flagged():
    script = {
        "options": [{"label": "A", "plain_language": "A filling.", "estimated_cost": "two hundred"}]
    }
    warnings = _validate_tc_script(script)
    assert any("estimated_cost" in w for w in warnings)


@patch("src.agents.base_agent._client")
def test_tc_agent_returns_validation_warnings(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps({
            "opening": "Let's discuss your options.",
            "options": [
                {"label": "Option A", "plain_language": "A filling.", "estimated_cost": 220},
            ],
            "recommendation_framing": "Dr. recommends Option A.",
            "follow_up_questions_to_anticipate": [],
            "documentation_note": "Reviewed.",
        }))]
    )
    agent = TreatmentCoordinatorAgent()
    result = agent.run(audit_result={"overall_assessment": "unsupported"})
    assert "validation_warnings" in result


# ── System prompts contain anti-hallucination language ────────────────────────

def test_all_system_prompts_contain_antihal_language():
    """Every agent that calls Claude must have explicit anti-hallucination language in its system prompt."""
    from src.agents.chart_agent import _SYSTEM as chart_sys
    from src.agents.research_agent import _RESEARCH_SYSTEM as research_sys
    from src.agents.documentation_agent import _DRAFT_SYSTEM as doc_draft_sys
    from src.agents.documentation_agent import _REVIEW_SYSTEM as doc_review_sys
    from src.agents.treatment_coordinator_agent import _TC_SYSTEM as tc_sys
    from src.agents.perio_chart_agent import _RECS_SYSTEM as perio_sys
    from src.agents.lab_case_agent import _SYSTEM as lab_sys
    from src.audit import _AUDIT_SYSTEM as audit_sys

    antihal_phrase = "anti-hallucination"

    for name, prompt in [
        ("ChartAgent", chart_sys),
        ("ResearchAgent", research_sys),
        ("DocumentationAgent._DRAFT", doc_draft_sys),
        ("DocumentationAgent._REVIEW", doc_review_sys),
        ("TreatmentCoordinatorAgent", tc_sys),
        ("PerioChartAgent._RECS", perio_sys),
        ("LabCaseAgent", lab_sys),
        ("audit._AUDIT_SYSTEM", audit_sys),
    ]:
        assert antihal_phrase.lower() in prompt.lower(), (
            f"{name} system prompt is missing anti-hallucination rules section."
        )
