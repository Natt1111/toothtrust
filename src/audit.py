"""Treatment plan auditor: compare proposed procedures against retrieved evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import anthropic

from src.agents.base_agent import BaseAgent
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
  "patient_summary": "<plain-language 2-3 sentence summary for the patient>",
  "recommended_alternative": {
    "cdt_code": "<code or null>",
    "description": "<procedure name>",
    "rationale": "<1 sentence why this alternative is more appropriate>",
    "estimated_fee": <number or null>
  }
}

The recommended_alternative field is REQUIRED when overall_assessment is "unsupported" or
"partially_supported". Set it to null when overall_assessment is "supported".

Anti-hallucination rules:
- ONLY cite source documents listed in the Evidence excerpts provided below. Never cite sources not in the context.
- Never fabricate CDT codes, clinical findings, or patient data not present in the input.
- overall_assessment must be one of the four allowed values; confidence must be high/medium/low.
- If the evidence does not support a conclusion, use "insufficient_evidence", not a fabricated rationale.
- Frame everything as informational — you are not diagnosing or prescribing."""

# Allowed values for post-processing validation
_VALID_ASSESSMENTS = {"supported", "partially_supported", "unsupported", "insufficient_evidence", "error"}
_VALID_VERDICTS = {"supported", "partially_supported", "unsupported", "insufficient_evidence"}
_VALID_CONFIDENCE = {"high", "medium", "low"}
_CDT_RE = re.compile(r"^D\d{4}$")


def _validate_audit_output(data: dict, chunks: list[dict]) -> list[str]:
    """Post-process audit JSON for hallucination signals. Returns list of warning strings."""
    warnings: list[str] = []
    allowed = {c["source"] for c in chunks}

    # overall_assessment must be a known value
    oa = data.get("overall_assessment", "")
    if oa not in _VALID_ASSESSMENTS:
        warnings.append(f"overall_assessment '{oa}' is not a valid value.")

    # confidence must be a known value
    conf = data.get("confidence", "")
    if conf not in _VALID_CONFIDENCE:
        warnings.append(f"confidence '{conf}' is not a valid value.")

    for i, proc in enumerate(data.get("procedures", [])):
        # Verdict validation
        verdict = proc.get("verdict", "")
        if verdict and verdict not in _VALID_VERDICTS:
            warnings.append(f"procedure[{i}].verdict '{verdict}' is not a valid value.")

        # CDT code format
        code = proc.get("cdt_code", "")
        if code and not _CDT_RE.match(code.strip()):
            warnings.append(f"procedure[{i}].cdt_code '{code}' does not match D####  format.")

        # Citation grounding — catch fabricated sources
        fabricated = BaseAgent._validate_citations(proc.get("citations", []), allowed)
        for fab in fabricated:
            warnings.append(
                f"procedure[{i}] cited '{fab}' which was not in the retrieved context — possible hallucination."
            )

    return warnings


@dataclass
class AuditResult:
    overall_assessment: str
    confidence: str
    procedures: list[dict]
    missing_information: list[str]
    patient_summary: str
    recommended_alternative: dict = field(default_factory=dict)
    validation_warnings: list[str] = field(default_factory=list)
    retrieved_chunks: list[dict] = field(default_factory=list)
    raw_response: str = ""


def audit_treatment_plan(
    treatment_plan: list[dict],
    patient_context: str = "",
    retriever: EvidenceRetriever | None = None,
) -> AuditResult:
    """Audit a treatment plan against evidence.

    Args:
        treatment_plan: List of dicts with keys: cdt_code, description, tooth (optional).
        patient_context: Free-text patient medical/dental history.
        retriever: EvidenceRetriever instance; created fresh if None.

    Returns:
        AuditResult with verdict per procedure, citations, and validation_warnings.
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
        data = BaseAgent._parse_json_response(raw)
    except ValueError:
        data = {
            "overall_assessment": "error",
            "confidence": "low",
            "procedures": [],
            "missing_information": [],
            "patient_summary": "Audit parsing failed. Please review the raw response.",
            "recommended_alternative": {},
        }

    warnings = _validate_audit_output(data, chunks)

    return AuditResult(
        overall_assessment=data.get("overall_assessment", ""),
        confidence=data.get("confidence", ""),
        procedures=data.get("procedures", []),
        missing_information=data.get("missing_information", []),
        patient_summary=data.get("patient_summary", ""),
        recommended_alternative=data.get("recommended_alternative") or {},
        validation_warnings=warnings,
        retrieved_chunks=chunks,
        raw_response=raw,
    )
