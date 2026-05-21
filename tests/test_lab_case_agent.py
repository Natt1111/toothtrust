"""Tests for LabCaseAgent — scan, lookup, attribution, check-in, and orchestrator routing.

All tests use mock data from data/mock_data/ and do NOT make Claude API calls,
except test_recommend_reschedules_calls_claude which patches the client.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.lab_case_agent import LabCaseAgent
from src.orchestrator import Intent, Orchestrator

_LAB_CASES_PATH = Path("data/mock_data/lab_cases.json")


# ── 1. Scan returns correct risk levels for all 8 appointments ────────────────

def test_scan_returns_all_appointments():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    assert result["intent"] == "lab_case_scan"
    assert len(result["appointments"]) == 8


def test_scan_risk_level_counts():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    summary = result["summary"]
    assert summary["on_track"] == 2
    assert summary["at_risk"] == 1
    assert summary["critical_missing"] == 3
    assert summary["no_case_required"] == 2


def test_scan_no_case_required_for_hygiene_and_exam():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    no_case = [r for r in result["appointments"] if r["risk_level"] == "no_case_required"]
    names = {r["patient_name"] for r in no_case}
    assert "Linda Patel" in names    # D0150 exam — no lab case
    assert "Patricia Lewis" in names  # D1110 prophy — no lab case


def test_scan_shipped_back_is_on_track():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    chen = next(r for r in result["appointments"] if r["patient_name"] == "Sarah Chen")
    assert chen["lab_case_status"] == "shipped_back"
    assert chen["risk_level"] == "on_track"


def test_scan_received_in_office_is_on_track():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    rodriguez = next(r for r in result["appointments"] if r["patient_name"] == "James Rodriguez")
    assert rodriguez["lab_case_status"] == "received_in_office"
    assert rodriguez["risk_level"] == "on_track"


def test_scan_overdue_no_update_is_critical():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    kim = next(r for r in result["appointments"] if r["patient_name"] == "David Kim")
    assert kim["lab_case_status"] == "overdue_no_update"
    assert kim["risk_level"] == "critical_missing"


def test_scan_in_transit_to_lab_with_less_48h_is_critical():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    gonzalez = next(r for r in result["appointments"] if r["patient_name"] == "Maria Gonzalez")
    assert gonzalez["lab_case_status"] == "in_transit_to_lab"
    assert gonzalez["risk_level"] == "critical_missing"


def test_scan_explicit_critical_missing_status_is_critical():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    johnson = next(r for r in result["appointments"] if r["patient_name"] == "Robert Johnson")
    assert johnson["lab_case_status"] == "critical_missing"
    assert johnson["risk_level"] == "critical_missing"


def test_scan_in_progress_future_return_is_at_risk():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    thompson = next(r for r in result["appointments"] if r["patient_name"] == "Michael Thompson")
    assert thompson["lab_case_status"] == "in_progress"
    assert thompson["risk_level"] == "at_risk"


def test_scan_voice_summary_mentions_critical_patients():
    agent = LabCaseAgent()
    result = agent.scan_tomorrows_appointments()
    voice = result["voice_summary"]
    assert "David Kim" in voice
    assert "Maria Gonzalez" in voice
    assert "Robert Johnson" in voice


# ── 2. Lookup with exact patient name ────────────────────────────────────────

def test_lookup_exact_name_returns_case():
    agent = LabCaseAgent()
    result = agent.lookup_case("Sarah Chen")
    assert result["found"] is True
    assert result["patient_name"] == "Sarah Chen"
    assert result["case_number"] == "LC-4401"
    assert result["lab_name"] == "Glidewell Dental Lab"
    assert result["risk_level"] == "on_track"
    assert result["days_until_appointment"] == 1


# ── 3. Fuzzy / partial name lookup still finds the case ──────────────────────

def test_lookup_partial_name_finds_case():
    agent = LabCaseAgent()
    result = agent.lookup_case("Chen")
    assert result["found"] is True
    assert result["patient_name"] == "Sarah Chen"


def test_lookup_lowercase_partial_name():
    agent = LabCaseAgent()
    result = agent.lookup_case("johnson")
    assert result["found"] is True
    assert result["patient_name"] == "Robert Johnson"


def test_lookup_unknown_name_returns_not_found():
    agent = LabCaseAgent()
    result = agent.lookup_case("Nonexistent Patient")
    assert result["found"] is False


# ── 4. Attribution correctly identifies broken handoff step ──────────────────

def test_attribution_broken_step_for_critical_missing():
    agent = LabCaseAgent()
    result = agent.attribution_check("LC-4406")
    assert result["found"] is True
    assert result["case_id"] == "LC-4406"
    assert result["patient_name"] == "Robert Johnson"
    assert result["last_completed_step"] == "sent_to_lab"
    assert result["broken_step"] == "lab_received"
    assert result["responsible_role"] == "Dental Lab"


def test_attribution_suggests_fix_not_blame():
    agent = LabCaseAgent()
    result = agent.attribution_check("LC-4406")
    # framing_note must exist and must NOT blame an individual
    framing = result["framing_note"].lower()
    assert "workflow gap" in framing
    assert "not individual failure" in framing or "not individual" in framing


def test_attribution_unknown_case_id():
    agent = LabCaseAgent()
    result = agent.attribution_check("LC-9999")
    assert result["found"] is False


def test_attribution_completed_case_has_no_broken_step():
    agent = LabCaseAgent()
    result = agent.attribution_check("LC-4402")  # received_in_office — all steps done
    assert result["found"] is True
    assert result["broken_step"] is None


# ── 5. check_in_case updates state and restores it ───────────────────────────

def test_check_in_case_updates_status():
    # Back up the lab_cases.json before mutating
    backup = _LAB_CASES_PATH.read_text()
    try:
        agent = LabCaseAgent()
        result = agent.check_in_case("Sarah Chen")
        assert result["success"] is True
        assert result["case_id"] == "LC-4401"
        assert result["updated_status"] == "received_in_office"

        # Verify the file was actually updated
        data = json.loads(_LAB_CASES_PATH.read_text())
        lc = next(c for c in data["lab_cases"] if c["case_id"] == "LC-4401")
        assert lc["current_status"] == "received_in_office"
        # A new office_received step should have been appended
        steps = [h["step"] for h in lc["handoff_history"]]
        assert "office_received" in steps
    finally:
        # Always restore the original file
        _LAB_CASES_PATH.write_text(backup)


def test_check_in_case_unknown_patient():
    agent = LabCaseAgent()
    result = agent.check_in_case("Nobody Here")
    assert result["success"] is False


# ── Orchestrator routing ──────────────────────────────────────────────────────

@patch("src.orchestrator._client")
def test_orchestrator_fast_path_scan(mock_client):
    orch = Orchestrator()
    intent = orch.classify_intent("scan tomorrow's lab cases")
    assert intent == Intent.LAB_CASE
    mock_client.messages.create.assert_not_called()  # fast-path — no LLM call


@patch("src.orchestrator._client")
def test_orchestrator_fast_path_where_is_case(mock_client):
    orch = Orchestrator()
    intent = orch.classify_intent("where's the Chen case")
    assert intent == Intent.LAB_CASE
    mock_client.messages.create.assert_not_called()


@patch("src.orchestrator._client")
def test_orchestrator_llm_classifies_lab_case(mock_client):
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="lab_case")]
    )
    orch = Orchestrator()
    intent = orch.classify_intent("check whether the Rodriguez restoration is back yet")
    assert intent == Intent.LAB_CASE
