"""Tests for the audit pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.audit import AuditResult, audit_treatment_plan


MOCK_PLAN = [
    {"cdt_code": "D2740", "description": "Crown - porcelain/ceramic substrate", "tooth": 19},
    {"cdt_code": "D4341", "description": "Periodontal scaling and root planing", "tooth": None},
]

MOCK_AUDIT_JSON = """{
  "overall_assessment": "partially_supported",
  "confidence": "medium",
  "procedures": [
    {
      "cdt_code": "D2740",
      "description": "Crown - porcelain/ceramic substrate",
      "verdict": "supported",
      "rationale": "Evidence supports crown placement for extensively restored teeth.",
      "flags": [],
      "citations": ["ADA_guidelines.pdf"]
    },
    {
      "cdt_code": "D4341",
      "description": "Periodontal scaling and root planing",
      "verdict": "partially_supported",
      "rationale": "SRP indicated for pockets ≥4mm with BOP; pocket depth not specified.",
      "flags": ["Pocket depth measurements not provided"],
      "citations": ["AAP_guidelines.pdf"]
    }
  ],
  "missing_information": ["Periodontal charting with pocket depths"],
  "patient_summary": "One of your two proposed procedures is well-supported by evidence."
}"""


def _mock_retriever():
    retriever = MagicMock()
    retriever.retrieve.return_value = [{"text": "Evidence text", "source": "ADA_guidelines.pdf", "score": 0.9}]
    retriever.format_context.return_value = "[1] Source: ADA_guidelines.pdf\nEvidence text"
    return retriever


@patch("src.audit._client")
def test_audit_returns_audit_result(mock_client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=MOCK_AUDIT_JSON)]
    mock_client.messages.create.return_value = mock_response

    result = audit_treatment_plan(MOCK_PLAN, retriever=_mock_retriever())

    assert isinstance(result, AuditResult)
    assert result.overall_assessment == "partially_supported"
    assert result.confidence == "medium"
    assert len(result.procedures) == 2


@patch("src.audit._client")
def test_audit_handles_json_parse_error(mock_client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]
    mock_client.messages.create.return_value = mock_response

    result = audit_treatment_plan(MOCK_PLAN, retriever=_mock_retriever())

    assert result.overall_assessment == "error"
    assert result.procedures == []


@patch("src.audit._client")
def test_audit_patient_summary_present(mock_client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=MOCK_AUDIT_JSON)]
    mock_client.messages.create.return_value = mock_response

    result = audit_treatment_plan(MOCK_PLAN, retriever=_mock_retriever())

    assert result.patient_summary
    assert len(result.patient_summary) > 10


@patch("src.audit._client")
def test_audit_procedure_flags(mock_client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=MOCK_AUDIT_JSON)]
    mock_client.messages.create.return_value = mock_response

    result = audit_treatment_plan(MOCK_PLAN, retriever=_mock_retriever())
    srp = next(p for p in result.procedures if p["cdt_code"] == "D4341")

    assert srp["flags"]
    assert any("pocket" in flag.lower() for flag in srp["flags"])
