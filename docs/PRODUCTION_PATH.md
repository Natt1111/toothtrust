# Production Path

This document tracks the gaps between the current MVP and a production-ready, HIPAA-compliant deployment.

## Milestone 1 — Demo-Ready (current)
- [x] Repo scaffolded
- [x] RAG pipeline (ingest → retrieve → audit)
- [x] Voice pipeline stub (STT → intent → TTS) — now also live in-app via the Voice Command page, not just the CLI demo
- [x] Mock Dentrix integration — in-memory only, zero disk persistence (`src/integrations/dentrix_mock.py`, guaranteed by `tests/test_dentrix_mock.py`)
- [x] Streamlit demo UI
- [ ] Populated evidence corpus (ADA guidelines, 3–5 Cochrane reviews)
- [ ] End-to-end audit demo with a real treatment plan PDF

## Milestone 2 — Pilot (1–2 dental offices)
- [ ] HIPAA Business Associate Agreement with all vendors (Anthropic, Deepgram, ElevenLabs) — the real bottleneck; a legal/vendor process, not engineering. Start in parallel with everything else in this milestone. Tracked with confirmed per-vendor requirements and ready-to-send outreach drafts in [docs/COMPLIANCE_BAA_TRACKER.md](COMPLIANCE_BAA_TRACKER.md) — outreach not yet sent.
- [ ] PHI handling audit — ensure no patient data written to logs or vector DB
  - [x] Chart/session storage confirmed in-memory-only, never written to disk (`Orchestrator._sessions`, `DentrixMock`)
  - [x] Vector DB (ChromaDB) confirmed to hold only general clinical evidence, never patient-specific data — true by construction, `EvidenceRetriever` has no patient-data write path
  - [ ] Log-line audit for agent error paths — some exception messages can currently echo request/response content into server-side `print()` output; needs a pass to confirm nothing patient-derived reaches persistent log storage
- [ ] De-identification layer before any data leaves the operatory
- [ ] Replace local ChromaDB with a managed, encrypted vector DB (e.g., Pinecone, Weaviate Cloud)
- [ ] Auth: practice-level API keys, per-user sessions
- [ ] Dentrix write-back via official API or HL7 FHIR bridge

## Milestone 3 — Scale
- [ ] Multi-tenant architecture (practice isolation)
- [ ] Corpus update pipeline — detect new ADA/Cochrane publications, auto-ingest
- [ ] Fine-tuned CDT code classifier for faster, cheaper charting
- [ ] iOS companion app with offline fallback (on-device whisper.cpp for STT)
- [ ] SOC 2 Type II audit
- [ ] ONC certification if billing codes are generated

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM hallucination in clinical context | Medium | High | Retrieval confidence score, mandatory citation display, "I don't know" fallback |
| HIPAA violation via log leakage | Low | Critical | Structured logging with PII scrubber, no patient name/DOB in any log line |
| Deepgram/ElevenLabs BAA unavailable | Low | High | Confirmed: Deepgram BAA available on request on qualifying plans. ElevenLabs BAA is **Enterprise-tier only** plus mandatory Zero Retention Mode — the recent ElevenLabs plan upgrade is very likely not Enterprise, so this may still be blocked; verify before assuming it's covered. See [docs/COMPLIANCE_BAA_TRACKER.md](COMPLIANCE_BAA_TRACKER.md). |
| Dentrix API access denied | Medium | High | HL7 FHIR export as fallback; manual paste-in flow for MVP |
| Evidence corpus copyright | Medium | Medium | License ADA content; rely on fair-use excerpts for research; consult IP counsel |
