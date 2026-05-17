# Architecture

## Overview

ToothTrust is a voice-first multimodal RAG platform composed of five cooperating layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│         Streamlit UI  ·  FastAPI  ·  Voice (mic/speaker)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      Orchestrator                               │
│         Routes intents to agents, manages session state         │
└──┬──────────────┬──────────────┬──────────────┬────────────────┘
   │              │              │              │
┌──▼──┐      ┌───▼───┐     ┌────▼────┐    ┌───▼────────────┐
│Chart│      │ Audit │     │Research │    │Documentation   │
│Agent│      │ Agent │     │  Agent  │    │    Agent       │
└──┬──┘      └───┬───┘     └────┬────┘    └───────┬────────┘
   │              │              │                  │
┌──▼──────────────▼──────────────▼──────────────────▼────────────┐
│                        RAG Core                                 │
│     ChromaDB  ·  Sentence-Transformers  ·  Claude claude-sonnet-4-6      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Data Layer                                 │
│    Evidence corpus (PDF/HTML)  ·  CDT codes  ·  Mock charts     │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### Voice Pipeline
- **Wake word**: Picovoice Porcupine ("Hey ToothTrust")
- **STT**: Deepgram Nova-2 (medical model)
- **Intent routing**: Claude classifies utterance → agent
- **TTS**: ElevenLabs (low-latency streaming)

### RAG Stack
- Corpus ingested from PDFs via `pypdf`, chunked and embedded with `sentence-transformers`
- Stored in ChromaDB (local dev) — swap to managed vector DB for production
- Retrieved chunks passed as context to Claude claude-sonnet-4-6

### Agent Layer
Each agent is a thin Claude API wrapper with a system prompt and tool definitions:
| Agent | Responsibility |
|---|---|
| ChartAgent | Parse voice utterance → structured chart entry |
| AuditAgent | Compare treatment plan against evidence corpus |
| ResearchAgent | Answer chairside clinical questions |
| DocumentationAgent | Generate patient-facing reports |

### Integrations
- `dentrix_mock.py` — stub that mimics Dentrix API surface for local dev
- `videa_mock.py` — stub that returns synthetic X-ray analysis results

## Data Flow: Treatment Plan Audit

```
Patient PDF / voice input
        │
        ▼
    vision.py (Claude Vision extracts findings)
        │
        ▼
    retrieval.py (embed findings → top-k evidence chunks)
        │
        ▼
    audit.py (Claude: findings + evidence → audit report)
        │
        ▼
    report.py (render patient-friendly HTML/PDF)
```

## Data Flow: Chairside Voice Charting

```
Microphone → wake_word.py → stt.py → intent_router.py
                                           │
                          ┌────────────────┘
                          │
                    chart_agent.py
                          │
                    dentrix_mock.py (write-back)
                          │
                    tts.py → speaker
```

## ADR Index

- [ADR-0001](ADR/0001-multimodal-rag-over-fine-tuning.md): Multimodal RAG over fine-tuning
