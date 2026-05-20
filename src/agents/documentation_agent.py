"""Documentation agent: ambient SOAP note capture with two-step draft → review → sign workflow.

Regulatory note: only the licensed dentist may finalize (sign) a clinical record. This agent
drafts and presents notes for review but never applies a signature autonomously. The sign action
must be explicitly authorized by a voice command from the clinician ("sign it", "I approve",
"sign the note").
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

_DRAFT_SYSTEM = """You are a dental clinical documentation specialist.
Generate a structured SOAP note from the clinician's dictation or session context.

Output ONLY valid JSON in this exact schema:
{
  "subjective": "<patient-reported symptoms, chief complaint, medical history relevant to today>",
  "objective": "<clinical findings, vitals, charted entries, radiographic findings>",
  "assessment": "<diagnosis or working diagnosis with CDT codes where applicable>",
  "plan": "<procedures performed today and follow-up plan>",
  "medications": "<anesthesia administered, prescriptions, medications noted>",
  "patient_response": "<patient cooperation, tolerance, any adverse reactions>",
  "cdt_codes": ["<code1>", "<code2>"]
}

Be concise and clinically precise. Use standard dental abbreviations (e.g., MOD, BOP, CAL).
Do not invent findings not present in the input. If a field has no data, use an empty string."""

_REVIEW_SYSTEM = """You are a dental clinical documentation reviewer.
The dentist is reviewing a drafted SOAP note by voice. Apply their requested changes precisely.
Return ONLY the updated note as valid JSON using the same schema as the original.
Do not add commentary. Do not change fields the dentist did not mention."""

from src.agents.base_agent import BaseAgent


class DocumentationAgent(BaseAgent):
    """Two-step documentation workflow: DRAFT then REVIEW & SIGN.

    Step 1 — DRAFT:
        Call run() with action="draft". Accepts a voice utterance, session chart entries,
        and an optional patient_name. Returns a SOAP note stored in session.documentation_draft
        with status "pending_review".

        v2 hook: ambient capture mode will call run(action="draft", ambient_transcript=...) to
        ingest a full-visit transcript rather than a single dictation utterance.

    Step 2 — REVIEW & SIGN:
        Call run() with action="review" and a voice command such as:
        - "read me the note" → returns the current draft formatted for reading aloud
        - "add: <text>, then sign" → appends the text and marks signed
        - "sign it" / "I approve" → marks the note as signed with timestamp

        The agent never signs autonomously. Only an explicit sign command from the clinician
        triggers signature application.
    """

    system_prompt = _DRAFT_SYSTEM
    max_tokens = 1024

    def run(
        self,
        utterance: str = "",
        session=None,
        action: str = "draft",
        format: str = "text",
        patient_name: str = "",
        appointment_time: str = "",
        **kwargs,
    ) -> dict:
        if action == "draft":
            return self._draft(utterance, session, patient_name, appointment_time)
        if action == "review":
            return self._review(utterance, session, patient_name, appointment_time)
        return {"intent": "document", "response": f"Unknown action '{action}'.", "status": "error"}

    # ------------------------------------------------------------------
    # Step 1: Draft
    # ------------------------------------------------------------------

    def _draft(
        self, utterance: str, session, patient_name: str, appointment_time: str
    ) -> dict:
        context_parts = [utterance] if utterance else []

        if session and session.chart_entries:
            entries_summary = json.dumps(session.chart_entries, indent=2)
            context_parts.append(f"Session chart entries:\n{entries_summary}")

        if session and session.audit_result:
            context_parts.append(
                f"Audit result summary:\n{getattr(session.audit_result, 'overall_assessment', '')}"
            )

        prompt = "\n\n".join(context_parts) or "No dictation provided — generate a minimal note."
        raw = self._call(prompt, system=_DRAFT_SYSTEM)

        try:
            note = json.loads(raw)
        except json.JSONDecodeError:
            note = {
                "subjective": utterance,
                "objective": "",
                "assessment": "",
                "plan": "",
                "medications": "",
                "patient_response": "",
                "cdt_codes": [],
            }

        draft = {
            "note": note,
            "patient_name": patient_name,
            "appointment_time": appointment_time or datetime.now(timezone.utc).isoformat(),
            "status": "pending_review",
            "signed_at": None,
        }

        if session is not None:
            session.documentation_draft = draft

        notification = (
            f"Note for {patient_name or 'this patient'}, "
            f"{appointment_time or 'today'}, is ready to review. "
            "Say 'read me the note', 'add: [text], then sign', or 'sign it'."
        )

        return {
            "intent": "document",
            "response": notification,
            "draft": draft,
            "status": "pending_review",
        }

    # ------------------------------------------------------------------
    # Step 2: Review & Sign
    # ------------------------------------------------------------------

    def _review(
        self, utterance: str, session, patient_name: str, appointment_time: str
    ) -> dict:
        draft = getattr(session, "documentation_draft", None) if session else None

        if not draft:
            return {
                "intent": "document",
                "response": "No draft found. Say 'draft the note' first.",
                "status": "no_draft",
            }

        cmd = utterance.lower().strip()

        if cmd in ("read me the note", "read the note", "read it"):
            return self._read_aloud(draft)

        if self._is_sign_command(cmd) and not cmd.startswith("add:"):
            return self._sign(draft, session)

        if cmd.startswith("add:"):
            return self._amend_and_maybe_sign(utterance, draft, session)

        # Generic amendment
        return self._amend(utterance, draft, session)

    def _read_aloud(self, draft: dict) -> dict:
        note = draft["note"]
        readable = (
            f"Subjective: {note.get('subjective', 'none')}. "
            f"Objective: {note.get('objective', 'none')}. "
            f"Assessment: {note.get('assessment', 'none')}. "
            f"Plan: {note.get('plan', 'none')}."
        )
        return {"intent": "document", "response": readable, "draft": draft, "status": "pending_review"}

    def _is_sign_command(self, cmd: str) -> bool:
        sign_phrases = ("sign it", "i approve", "sign the note", "approve the note", "looks good sign it")
        return any(cmd == phrase or cmd.endswith(phrase) for phrase in sign_phrases)

    def _sign(self, draft: dict, session) -> dict:
        draft["status"] = "signed"
        draft["signed_at"] = datetime.now(timezone.utc).isoformat()
        if session is not None:
            session.documentation_draft = draft
        patient = draft.get("patient_name") or "patient"
        return {
            "intent": "document",
            "response": f"Note for {patient} signed and finalized.",
            "draft": draft,
            "status": "signed",
        }

    def _amend_and_maybe_sign(self, utterance: str, draft: dict, session) -> dict:
        lower = utterance.lower()
        sign_after = ", then sign" in lower or " then sign" in lower
        addition = utterance.split("add:", 1)[-1]
        if sign_after:
            addition = addition.replace(", then sign", "").replace(" then sign", "")

        draft = self._apply_amendment(addition.strip(), draft, session)
        if sign_after:
            return self._sign(draft, session)
        return {
            "intent": "document",
            "response": "Amendment applied. Say 'sign it' to finalize.",
            "draft": draft,
            "status": "pending_review",
        }

    def _amend(self, utterance: str, draft: dict, session) -> dict:
        draft = self._apply_amendment(utterance, draft, session)
        return {
            "intent": "document",
            "response": "Amendment applied. Say 'sign it' to finalize.",
            "draft": draft,
            "status": "pending_review",
        }

    def _apply_amendment(self, amendment_text: str, draft: dict, session) -> dict:
        current_note_json = json.dumps(draft["note"])
        prompt = f"Current note:\n{current_note_json}\n\nAmendment requested: {amendment_text}"
        raw = self._call(prompt, system=_REVIEW_SYSTEM)
        try:
            draft["note"] = json.loads(raw)
        except json.JSONDecodeError:
            plan = draft["note"].get("plan", "")
            draft["note"]["plan"] = f"{plan} | Amendment: {amendment_text}".strip(" | ")
        if session is not None:
            session.documentation_draft = draft
        return draft
