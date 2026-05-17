"""Research agent: answer chairside clinical questions using RAG."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.retrieval import EvidenceRetriever

_retriever = EvidenceRetriever()

_RESEARCH_SYSTEM = """You are a chairside dental clinical reference assistant.
Answer the clinician's question concisely (2-4 sentences) using the evidence excerpts provided.
Always cite the source document by name. If the evidence doesn't cover the question, say so.
Frame responses as informational, not prescriptive. Be direct — the clinician is in the middle of a procedure."""


class ResearchAgent(BaseAgent):
    system_prompt = _RESEARCH_SYSTEM
    max_tokens = 512

    def run(self, utterance: str, session=None, **kwargs) -> dict:
        chunks = _retriever.retrieve(utterance, top_k=3)
        context = _retriever.format_context(chunks)
        prompt = f"Evidence:\n{context}\n\nQuestion: {utterance}"
        answer = self._call(prompt, system=_RESEARCH_SYSTEM)
        return {
            "intent": "research",
            "response": answer,
            "sources": [c["source"] for c in chunks],
        }
