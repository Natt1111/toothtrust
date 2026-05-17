# ADR-0001: Multimodal RAG over Fine-Tuning

**Status**: Accepted  
**Date**: 2026-05-17  
**Deciders**: ToothTrust core team

---

## Context

ToothTrust needs to ground clinical recommendations in current, auditable evidence — ADA guidelines, Cochrane reviews, peer-reviewed journals. Two architectural approaches are viable:

1. **Fine-tune** a foundation model on dental literature so the model "memorizes" the evidence.
2. **Retrieval-Augmented Generation (RAG)** — keep the foundation model frozen, retrieve relevant passages at inference time, and pass them as context.

## Decision

We use **multimodal RAG with Claude claude-sonnet-4-6** as the generator, ChromaDB as the vector store, and `sentence-transformers/all-MiniLM-L6-v2` as the retrieval encoder.

## Rationale

| Criterion | Fine-tuning | RAG |
|---|---|---|
| Evidence currency | Requires re-training when guidelines update | Update the corpus, no model change |
| Auditability | Model internals opaque | Retrieved chunks are inspectable citations |
| Cost at MVP scale | High (GPU training + hosting) | Low (API calls + local ChromaDB) |
| Multimodal (X-ray) | Would require MLLM fine-tune | Claude Vision handles images natively |
| Time to first demo | Weeks | Days |
| Regulatory traceability | Hard — can't point to source | Each claim maps to a retrieved passage |

For a clinical product, **auditability and evidence currency are non-negotiable**. A dentist or patient challenging a recommendation must be able to see exactly which guideline passage the system cited. RAG makes this trivial; fine-tuning makes it nearly impossible.

## Trade-offs Accepted

- **Retrieval quality ceiling**: If the encoder misses a relevant passage, the LLM never sees it. Mitigation: hybrid BM25 + dense retrieval in a future iteration.
- **Context window cost**: Stuffing retrieved passages into every prompt increases token spend. Mitigation: prompt caching (Anthropic cache-control headers).
- **Hallucination risk on out-of-corpus queries**: Claude may still hallucinate when retrieval returns irrelevant chunks. Mitigation: AuditAgent returns a confidence score and flags low-retrieval-quality responses.

## Consequences

- The corpus pipeline (`ingest.py`) becomes a first-class component — quality of evidence ingestion directly determines recommendation quality.
- The system is explainable by design: every audit report can list the source documents.
- Fine-tuning remains an option for v2 if we need sub-100ms on-device inference for offline operatories.
