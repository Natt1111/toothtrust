"""Lab Case Agent: proactive lab case risk scanning and handoff attribution.

Reads appointment and lab case data from mock Dentrix interfaces and surfaces
at-risk appointments before they become same-day surprises.

MOCK INTERFACE NOTE: All Dentrix read/write operations in v1 use local JSON files
in data/mock_data/. Production integration uses the Henry Schein One LinkIt API
(launched August 2025). Any reference to Dentrix Lab Case Manager reflects
publicly documented Dentrix behavior only — no internal API endpoints are inferred.

See docs/ADR/0004-lab-case-agent-positioning.md for architectural rationale.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.config import BASE_DIR

# Paths to mock data (v1). Swap these for LinkIt API calls in production.
_APPOINTMENTS_PATH = BASE_DIR / "data" / "mock_data" / "appointments.json"
_LAB_CASES_PATH    = BASE_DIR / "data" / "mock_data" / "lab_cases.json"

# Demo reference date — the "today" for Case 4 is 2026-05-21; tomorrow is 2026-05-22.
_DEMO_TODAY = datetime(2026, 5, 21)

_SYSTEM = """You are a dental office operational assistant, complementary to Dentrix Lab Case Manager.
Your job is to surface lab case risk information to front desk staff and office managers
in plain, actionable language suitable for voice readback.

Rules:
- Keep voice responses under 80 words.
- When summarizing a scan, lead with the count of critical or at-risk cases.
- In attribution analysis, describe workflow gaps, never blame individual staff members.
- Output structured JSON for UI rendering; include a "voice_summary" field for TTS.
- You are COMPLEMENTARY to Dentrix Lab Case Manager — you surface its data proactively.
  Never imply Dentrix is insufficient; the gap is workflow ownership, not feature gaps.
- Mark all data as informational; staff must verify in Dentrix before acting."""

# Token count of _SYSTEM: ~145 tokens — well within the 800-token budget.


class LabCaseAgent(BaseAgent):
    """Proactive lab case risk scanner for front desk and office managers.

    Methods are designed for both voice invocation (via Orchestrator) and
    direct programmatic use (via Streamlit UI and scripts/run_audit.py).

    All Dentrix interaction is mocked in v1 via local JSON files.
    Production: Henry Schein One LinkIt API.
    """

    system_prompt = _SYSTEM
    max_tokens = 512

    # ── Data loaders ──────────────────────────────────────────────────────────

    @staticmethod
    def _load_appointments() -> list[dict]:
        return json.loads(_APPOINTMENTS_PATH.read_text())["appointments"]

    @staticmethod
    def _load_lab_cases() -> list[dict]:
        return json.loads(_LAB_CASES_PATH.read_text())["lab_cases"]

    @staticmethod
    def _cases_by_id(lab_cases: list[dict]) -> dict[str, dict]:
        return {lc["case_id"]: lc for lc in lab_cases}

    # ── Risk classification ───────────────────────────────────────────────────

    @staticmethod
    def _classify_risk(apt: dict, lab_case: dict | None, today: datetime) -> str:
        """Return one of: on_track | at_risk | critical_missing | no_case_required."""
        if not apt.get("requires_lab_case"):
            return "no_case_required"
        if lab_case is None:
            return "critical_missing"
        status = lab_case.get("current_status", "")
        if status == "received_in_office":
            return "on_track"
        if status == "critical_missing":
            return "critical_missing"
        if status == "overdue_no_update":
            return "critical_missing"
        if status == "shipped_back":
            # Case is shipped — on track unless expected return is already past
            expected = lab_case.get("expected_return", "")
            if expected:
                exp_dt = datetime.fromisoformat(expected)
                appt_dt = datetime.fromisoformat(f"2026-05-22")
                if exp_dt < today:
                    return "at_risk"
            return "on_track"
        if status == "in_transit_to_lab":
            # Sent but lab hasn't confirmed receipt — risky with < 48 h to appointment
            appt_dt = datetime.fromisoformat("2026-05-22")
            hours_to_appt = (appt_dt - today).total_seconds() / 3600
            return "critical_missing" if hours_to_appt < 48 else "at_risk"
        if status == "in_progress":
            expected = lab_case.get("expected_return", "")
            if expected:
                exp_dt = datetime.fromisoformat(expected)
                appt_dt = datetime.fromisoformat("2026-05-22")
                if exp_dt > appt_dt:
                    return "at_risk"
            return "on_track"
        return "at_risk"

    @staticmethod
    def _recommended_action(risk: str, lab_case: dict | None) -> str:
        if risk == "no_case_required":
            return "No action needed — this appointment does not require a lab case."
        if risk == "on_track":
            return "No action needed — case is on track."
        if risk == "at_risk":
            lab = lab_case.get("lab_name", "[Lab Name]") if lab_case else "[Lab Name]"
            return f"Contact {lab} to confirm shipping status and expected delivery date."
        if risk == "critical_missing":
            if lab_case and lab_case.get("current_status") == "in_transit_to_lab":
                lab = lab_case.get("lab_name", "[Lab Name]")
                return (
                    f"URGENT: Contact {lab} immediately to confirm receipt and get ETA. "
                    "Consider calling patient to discuss possible reschedule."
                )
            return (
                "URGENT: Case has had no update since it was sent. "
                "Verify with lab immediately. Consider proactive patient reschedule."
            )
        return "Review case status in Dentrix Lab Case Manager."

    # ── Public methods ────────────────────────────────────────────────────────

    def scan_tomorrows_appointments(self, today: datetime | None = None) -> dict:
        """Scan all tomorrow's appointments and classify lab case risk for each.

        Returns a structured result with per-appointment risk and summary counts.
        Suitable for voice readback (voice_summary field) and UI rendering.
        """
        today = today or _DEMO_TODAY
        appointments = self._load_appointments()
        lab_cases = self._cases_by_id(self._load_lab_cases())

        results = []
        counts = {"on_track": 0, "at_risk": 0, "critical_missing": 0, "no_case_required": 0}

        for apt in appointments:
            lc_id = apt.get("lab_case_id")
            lab_case = lab_cases.get(lc_id) if lc_id else None
            risk = self._classify_risk(apt, lab_case, today)
            counts[risk] += 1
            results.append({
                "appointment_id": apt["appointment_id"],
                "patient_name": apt["patient_name"],
                "time": apt["time"],
                "procedure": apt["procedure_name"],
                "procedure_code": apt["procedure_code"],
                "lab_case_id": lc_id,
                "lab_case_status": lab_case["current_status"] if lab_case else "no_case",
                "lab_name": lab_case.get("lab_name") if lab_case else None,
                "risk_level": risk,
                "recommended_action": self._recommended_action(risk, lab_case),
            })

        critical_names = [r["patient_name"] for r in results if r["risk_level"] == "critical_missing"]
        at_risk_names  = [r["patient_name"] for r in results if r["risk_level"] == "at_risk"]

        if critical_names:
            voice = (
                f"{counts['critical_missing']} critical lab case issue"
                f"{'s' if counts['critical_missing'] > 1 else ''} for tomorrow: "
                f"{', '.join(critical_names)}. "
                f"{counts['at_risk']} at risk. Immediate action required."
            )
        elif at_risk_names:
            voice = (
                f"No critical issues, but {counts['at_risk']} case"
                f"{'s are' if counts['at_risk'] > 1 else ' is'} at risk: "
                f"{', '.join(at_risk_names)}. Recommend contacting labs today."
            )
        else:
            voice = (
                f"All {counts['on_track']} lab cases for tomorrow are on track. No action needed."
            )

        return {
            "intent": "lab_case_scan",
            "scan_date": "2026-05-22",
            "appointments": results,
            "summary": counts,
            "voice_summary": voice,
            "response": voice,
        }

    def lookup_case(self, patient_name_or_id: str) -> dict:
        """Look up lab case status for a patient by name or ID.

        Uses simple substring matching for voice queries (e.g., "where's the Chen case").
        Returns full case detail with recommended action and days until appointment.
        """
        query = patient_name_or_id.strip().lower()
        appointments = self._load_appointments()
        lab_cases_list = self._load_lab_cases()
        cases_by_id = self._cases_by_id(lab_cases_list)

        # Find matching appointment
        matched_apt = None
        for apt in appointments:
            if (query in apt["patient_name"].lower() or
                    query in apt["patient_id"].lower()):
                matched_apt = apt
                break

        if matched_apt is None:
            return {
                "intent": "lab_case_lookup",
                "found": False,
                "response": f"No appointment found matching '{patient_name_or_id}' for tomorrow.",
                "voice_summary": f"I couldn't find an appointment for {patient_name_or_id} tomorrow.",
            }

        lc_id = matched_apt.get("lab_case_id")
        lab_case = cases_by_id.get(lc_id) if lc_id else None

        if lab_case is None:
            return {
                "intent": "lab_case_lookup",
                "found": True,
                "patient_name": matched_apt["patient_name"],
                "appointment_time": matched_apt["time"],
                "requires_lab_case": matched_apt["requires_lab_case"],
                "lab_case": None,
                "response": (
                    f"{matched_apt['patient_name']} is scheduled at {matched_apt['time']} "
                    f"for {matched_apt['procedure_name']}. No lab case required."
                ),
                "voice_summary": (
                    f"{matched_apt['patient_name']} at {matched_apt['time']} — no lab case needed."
                ),
            }

        appt_date = datetime(2026, 5, 22)
        today = _DEMO_TODAY
        days_until = (appt_date - today).days
        risk = self._classify_risk(matched_apt, lab_case, today)
        action = self._recommended_action(risk, lab_case)

        voice = (
            f"{lab_case['patient_name']}'s case at {lab_case['lab_name']} — "
            f"status: {lab_case['current_status'].replace('_', ' ')}. "
            f"Appointment in {days_until} day{'s' if days_until != 1 else ''}. "
            f"{action[:60]}."
        )

        return {
            "intent": "lab_case_lookup",
            "found": True,
            "patient_name": lab_case["patient_name"],
            "appointment_time": matched_apt["time"],
            "case_number": lab_case["case_id"],
            "lab_name": lab_case["lab_name"],
            "procedure": lab_case["procedure"],
            "date_sent": lab_case["date_sent"],
            "expected_return": lab_case["expected_return"],
            "current_status": lab_case["current_status"],
            "last_update": lab_case["last_update_timestamp"],
            "days_until_appointment": days_until,
            "risk_level": risk,
            "recommended_action": action,
            "voice_summary": voice,
            "response": voice,
        }

    def check_in_case(self, patient_name_or_id: str, lab_case_id: str | None = None) -> dict:
        """Mark a lab case as received in office.

        Updates mock lab_cases.json in place (mock of Dentrix Lab Case Manager check-in).
        In production: POST to Henry Schein One LinkIt API to update case status.

        MOCK WRITE NOTE: Modifies data/mock_data/lab_cases.json directly.
        This simulates the Dentrix Lab Case Manager 'check in' action.
        """
        query = patient_name_or_id.strip().lower()
        data = json.loads(_LAB_CASES_PATH.read_text())
        lab_cases = data["lab_cases"]

        target = None
        for lc in lab_cases:
            if (lab_case_id and lc["case_id"] == lab_case_id) or (
                query in lc["patient_name"].lower() or query in lc["patient_id"].lower()
            ):
                target = lc
                break

        if target is None:
            return {
                "intent": "lab_case_check_in",
                "success": False,
                "response": f"No lab case found for '{patient_name_or_id}'.",
                "voice_summary": f"I couldn't find a lab case for {patient_name_or_id}.",
            }

        now_ts = datetime.now().isoformat(timespec="seconds")
        target["current_status"] = "received_in_office"
        target["last_update_timestamp"] = now_ts
        target["handoff_history"].append({
            "step": "office_received",
            "timestamp": now_ts,
            "role_responsible": "front_desk",
            "notes": "Marked received via ToothTrust LabCaseAgent voice command.",
        })

        _LAB_CASES_PATH.write_text(json.dumps(data, indent=2))

        voice = (
            f"Got it — {target['patient_name']}'s case has been marked received in office. "
            f"Case {target['case_id']} from {target['lab_name']} is checked in."
        )
        return {
            "intent": "lab_case_check_in",
            "success": True,
            "case_id": target["case_id"],
            "patient_name": target["patient_name"],
            "updated_status": "received_in_office",
            "timestamp": now_ts,
            "voice_summary": voice,
            "response": voice,
        }

    def recommend_reschedules(self) -> dict:
        """Draft patient-facing reschedule messages for all critical_missing cases.

        Uses Claude to write professional, empathetic messages.
        Suggests a specific alternative date (+7 days from original appointment).
        """
        scan = self.scan_tomorrows_appointments()
        critical = [r for r in scan["appointments"] if r["risk_level"] == "critical_missing"]

        if not critical:
            voice = "No critical lab case issues — no reschedules needed for tomorrow."
            return {
                "intent": "lab_case_reschedule",
                "reschedules_needed": 0,
                "drafts": [],
                "voice_summary": voice,
                "response": voice,
            }

        drafts = []
        for apt in critical:
            suggested_date = "2026-05-29"  # +7 days from 2026-05-22
            prompt = (
                f"Write a brief, professional, apologetic dental office reschedule message for a patient. "
                f"Patient name: {apt['patient_name']}. "
                f"Original appointment: May 22, 2026 at {apt['time']}. "
                f"Reason: The dental laboratory has not returned the required dental appliance in time. "
                f"Suggested new date: {suggested_date}. "
                f"Keep it under 60 words. Warm but professional tone. "
                f"Do not mention specific lab names or internal case numbers."
            )
            message = self._call(prompt)
            drafts.append({
                "patient_name": apt["patient_name"],
                "original_appointment": f"2026-05-22 at {apt['time']}",
                "suggested_new_date": suggested_date,
                "draft_message": message,
            })

        voice = (
            f"{len(drafts)} reschedule draft{'s' if len(drafts) > 1 else ''} ready — "
            f"{', '.join(d['patient_name'] for d in drafts)}."
        )
        return {
            "intent": "lab_case_reschedule",
            "reschedules_needed": len(drafts),
            "drafts": drafts,
            "voice_summary": voice,
            "response": voice,
        }

    def attribution_check(self, lab_case_id: str) -> dict:
        """Identify the broken handoff step for a lab case.

        Returns the handoff timeline and the last completed step, framing any gap
        as a workflow issue — never as individual blame.

        The 'broken step' is the step AFTER the last recorded timestamp in handoff_history.
        """
        lab_cases = self._load_lab_cases()
        target = next((lc for lc in lab_cases if lc["case_id"] == lab_case_id), None)

        if target is None:
            return {
                "intent": "lab_case_attribution",
                "found": False,
                "response": f"No lab case found with ID {lab_case_id}.",
                "voice_summary": f"Lab case {lab_case_id} not found.",
            }

        _STEP_ORDER = [
            "created", "sent_to_lab", "lab_received",
            "lab_in_progress", "lab_shipped", "office_received",
        ]
        _ROLE_LABEL = {
            "created":       ("dental_assistant", "Dental Assistant / Clinical Team"),
            "sent_to_lab":   ("dental_assistant", "Dental Assistant / Clinical Team"),
            "lab_received":  ("lab",               "Dental Lab"),
            "lab_in_progress": ("lab",             "Dental Lab"),
            "lab_shipped":   ("lab",               "Dental Lab"),
            "office_received": ("front_desk",      "Front Desk / Office Manager"),
        }
        _SUGGESTED_FIX = {
            "lab_received":  "No receipt confirmation on file. Contact the lab to confirm they received the case and establish an ETA. Add tracking numbers to future outbound shipments.",
            "lab_in_progress": "Lab receipt confirmed but no progress update. Contact the lab for a status update and estimated completion date.",
            "lab_shipped": "Lab has been working on the case but hasn't shipped. Contact the lab for an updated ship date.",
            "office_received": "Case was shipped back but hasn't been checked in. Check the office for the package and check it into Dentrix Lab Case Manager.",
        }

        history = target.get("handoff_history", [])
        completed_steps = {h["step"] for h in history}
        last_step = history[-1]["step"] if history else None

        # Find the first step in canonical order that was never completed
        broken_step = None
        for step in _STEP_ORDER:
            if step not in completed_steps:
                broken_step = step
                break

        role_key, role_label = _ROLE_LABEL.get(broken_step, ("unknown", "Unknown")) if broken_step else ("unknown", "Unknown")
        suggested_fix = _SUGGESTED_FIX.get(broken_step, "Review the full case history in Dentrix Lab Case Manager and contact the lab directly.") if broken_step else "All steps are complete."

        voice = (
            f"For {target['patient_name']}'s case: the workflow stopped after '{last_step.replace('_', ' ')}'. "
            f"The missing step is '{broken_step.replace('_', ' ') if broken_step else 'none'}'. "
            f"Recommended fix: {suggested_fix[:80]}."
        ) if broken_step else (
            f"{target['patient_name']}'s case has all steps complete."
        )

        return {
            "intent": "lab_case_attribution",
            "found": True,
            "case_id": target["case_id"],
            "patient_name": target["patient_name"],
            "handoff_history": history,
            "last_completed_step": last_step,
            "broken_step": broken_step,
            "responsible_role": role_label,
            "suggested_fix": suggested_fix,
            "framing_note": "This reflects a workflow gap, not individual failure. Standard practice does not always include automated receipt confirmation from labs.",
            "voice_summary": voice,
            "response": voice,
        }

    def run(self, utterance: str = "", session=None, sub_intent: str = "", **kwargs) -> dict:
        """Route voice utterance to the appropriate LabCaseAgent method."""
        u = utterance.lower()
        if sub_intent == "scan" or any(p in u for p in ("scan", "tomorrow", "lab cases at risk")):
            return self.scan_tomorrows_appointments()
        if sub_intent == "check_in" or "mark" in u or "received" in u or "check in" in u:
            patient = kwargs.get("patient_name_or_id", "") or utterance
            return self.check_in_case(patient)
        if sub_intent == "reschedule" or "reschedule" in u:
            return self.recommend_reschedules()
        if sub_intent == "attribution" or "fell through" in u or "attribution" in u:
            case_id = kwargs.get("lab_case_id", "")
            return self.attribution_check(case_id)
        # Default: treat utterance as a patient name lookup
        patient = kwargs.get("patient_name_or_id", utterance)
        return self.lookup_case(patient)
