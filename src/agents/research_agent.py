"""Research agent: answer chairside clinical questions using RAG."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.retrieval import EvidenceRetriever

_retriever = EvidenceRetriever()

_RESEARCH_SYSTEM = """You are a chairside dental clinical reference assistant.
Answer the clinician's question concisely (2-4 sentences) using ONLY the evidence excerpts provided.
Always cite the source document by name. If the evidence doesn't cover the question, say exactly:
"Not found in the evidence corpus." — do not fabricate an answer.
Frame responses as informational, not prescriptive. Be direct — the clinician is in the middle of a procedure.

Anti-hallucination rules:
- ONLY cite documents listed in the Evidence section provided to you. Never cite documents you were not given.
- If the evidence excerpts do not contain a relevant answer, respond "Not found in the evidence corpus."
- Never invent CDT codes, drug names, dosages, or clinical protocols not present in the evidence."""


class ResearchAgent(BaseAgent):
    system_prompt = _RESEARCH_SYSTEM
    max_tokens = 512

    def run(self, utterance: str, session=None, **kwargs) -> dict:
        chunks = _retriever.retrieve(utterance, top_k=3)
        allowed_sources = {c["source"] for c in chunks}
        context = _retriever.format_context(chunks)
        prompt = f"Evidence:\n{context}\n\nQuestion: {utterance}"
        answer = self._call(prompt, system=_RESEARCH_SYSTEM)

        # Validate that the response doesn't begin with an AI-speaker preamble
        warnings: list[str] = []
        if self._has_ai_preamble(answer):
            warnings.append(
                "Response begins with an AI-speaker preamble rather than evidence-grounded content."
            )

        # Surface only sources that were actually retrieved
        cited_sources = [c["source"] for c in chunks]
        fabricated = self._validate_citations(cited_sources, allowed_sources)
        if fabricated:
            warnings.append(f"Source(s) not in retrieved context: {fabricated}")

        return {
            "intent": "research",
            "response": answer,
            "sources": cited_sources,
            "validated_sources": [s for s in cited_sources if s in allowed_sources],
            "validation_warnings": warnings,
        }
