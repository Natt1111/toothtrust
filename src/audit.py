"""Treatment plan auditor: compare proposed procedures against retrieved evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from src.retrieval import EvidenceRetriever

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_AUDIT_SYSTEM = """You are an evidence-based dental treatment auditor.
You receive a proposed treatment plan and excerpts from clinical guidelines and research.
Your task is to evaluate each proposed procedure against the evidence and flag concerns.

Return ONLY valid JSON with this schema:
{
  "overall_assessment": "supported|partially_supported|unsupported|insufficient_evidence",
  "confidence": "high|medium|low",
  "procedures": [
    {
      "cdt_code": "<code>",
      "description": "<procedure>",
      "verdict": "supported|partially_supported|unsupported|insufficient_evidence",
      "rationale": "<1-2 sentence evidence-based rationale>",
      "flags": ["<any concerns, contraindications, or missing information>"],
      "citations": ["<source names from the provided context>"]
    }
  ],
  "missing_information": ["<what additional clinical data would improve confidence>"],
  "patient_summary": "<plain-language 2-3 sentence summary for the patient>"
}

You MUST cite only sources provided in the context. Do not fabricate citations.
Frame everything as informational — you are not diagnosing or prescribing."""


@dataclass
class AuditResult:
    overall_assessment: str
    confidence: str
    procedures: list[dict]
    missing_information: list[str]
    patient_summary: str
    retrieved_chunks: list[dict] = field(default_factory=list)
    raw_response: str = ""


def audit_treatment_plan(
    treatment_plan: list[dict],
    patient_context: str = "",
    retriever: EvidenceRetriever | None = None,
) -> AuditResult:
    """
    Audit a treatment plan against evidence.

    Args:
        treatment_plan: List of dicts with keys: cdt_code, description, tooth (optional).
        patient_context: Free-text patient medical/dental history.
        retriever: EvidenceRetriever instance; created fresh if None.

    Returns:
        AuditResult with verdict per procedure and citations.
    """
    if retriever is None:
        retriever = EvidenceRetriever()

    plan_text = json.dumps(treatment_plan, indent=2)
    query = f"evidence for dental procedures: {', '.join(p.get('description', '') for p in treatment_plan)}"
    if patient_context:
        query += f". Patient context: {patient_context}"

    chunks = retriever.retrieve(query)
    context = retriever.format_context(chunks)

    prompt = f"""Patient context: {patient_context or 'Not provided'}

Proposed treatment plan:
{plan_text}

Evidence excerpts:
{context}

Audit the treatment plan against the evidence above."""

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_AUDIT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "overall_assessment": "error",
            "confidence": "low",
            "procedures": [],
            "missing_information": [],
            "patient_summary": "Audit parsing failed. Please review the raw response.",
        }

    return AuditResult(
        overall_assessment=data.get("overall_assessment", ""),
        confidence=data.get("confidence", ""),
        procedures=data.get("procedures", []),
        missing_information=data.get("missing_information", []),
        patient_summary=data.get("patient_summary", ""),
        retrieved_chunks=chunks,
        raw_response=raw,
    )
