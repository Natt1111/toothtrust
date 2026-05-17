"""Intent routing: maps a transcribed utterance to a structured action request."""

from __future__ import annotations

from src.orchestrator import Orchestrator

_orchestrator = Orchestrator()


def route_utterance(session_id: str, utterance: str, patient_id: str = "") -> dict:
    """
    Classify and route a transcribed utterance through the orchestrator.
    Returns the agent response dict suitable for TTS or display.
    """
    return _orchestrator.route(session_id=session_id, utterance=utterance, patient_id=patient_id)
