# ToothTrust

> Voice-first multi-agent platform for the dental office.

**[🦷 Live Demo → toothtrust-app.streamlit.app](https://toothtrust-app.streamlit.app/)**

---

## Run Locally

```bash
git clone https://github.com/Natt1111/toothtrust.git && cd toothtrust
uv venv --python 3.11 && source .venv/bin/activate

# Streamlit demo only (no voice):
uv pip install -r requirements.txt

# Full local dev including voice pipeline:
uv pip install -r requirements-local.txt

cp .env.example .env   # add your ANTHROPIC_API_KEY
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python streamlit run app/streamlit_app.py
```

Opens at `http://localhost:8501`. Each live run costs ~$0.05. Results cached in session.  
Works in **offline mode** (no API key) — shows pre-computed results for all 4 cases.

Hosted on Streamlit Community Cloud → **[toothtrust-app.streamlit.app](https://toothtrust-app.streamlit.app/)**

---

## Problem

ToothTrust is a voice-first multi-agent platform for the dental office. Every staff role — assistant, hygienist, treatment coordinator, front desk, and dentist — has a specialized AI copilot that works hands-free through voice commands. LabCaseAgent is complementary to Dentrix Lab Case Manager: it surfaces lab case risk proactively so front desk staff catch issues before patients arrive, not after.

The core problem: dental staff are always busy with their hands. Gloves, instruments, patient contact. Every time someone needs to look something up, chart a finding, explain a procedure, or document a visit, they have to stop what they're doing. That friction compounds across 20+ patients a day per provider.

The voice layer removes that friction for every role. The agent layer gives each role the specific AI capability they need.

---

## Agent Platform

### v1 — Live

| Agent | Target User | Voice Command Example | Core Job |
|---|---|---|---|
| ChartAgent | Dental Assistant | "Chart MOD composite on 19" | Voice → structured chart entry + CDT code |
| AuditAgent | Dentist / Patient | "Is this crown justified?" | Treatment plan audit with evidence citations |
| ResearchAgent | Any clinical staff | "Bisphosphonate contraindications?" | Chairside RAG question answering |
| DocumentationAgent | Dentist | "Draft the note" / "Sign it" | Ambient SOAP note draft → voice review → sign |
| TreatmentCoordinatorAgent | Treatment Coordinator | "Explain this to the patient" | Audit result → plain-language patient script |
| PerioChartAgent | Hygienist | "Tooth 3 distobuccal 4 buccal 3..." | Voice probe calls → structured perio chart + AAP staging |
| LabCaseAgent | Front Desk / Office Manager | "Scan tomorrow's lab cases" | Proactive lab case risk scan + handoff attribution |

### v2 — Designed, not yet built

| Agent | Target User | Core Job |
|---|---|---|
| EducationAgent | Any staff | Voice-triggered procedure video on operatory screen |
| XRayRecallAgent | Dentist | "Pull up tooth 19" → opens correct radiograph |
| PhasingAgent | Dentist / TC | Organizes treatment plan into Phase 1–4 |
| PriorityAgent | Dentist | "What should we start today?" given time and clinical context |

See [docs/IDEAS.md](docs/IDEAS.md) for full v2 specs.

---

## Where this fits in the dental AI landscape

VideaHealth, Pearl, and Overjet solve the imaging interpretation problem — they find pathology in X-rays. ToothTrust is what happens after the AI finds something: chart it, audit the resulting treatment plan, explain it to the patient, document it, chart the perio exam. Complementary infrastructure, not a competitor.

---

## Architecture

Full architecture narrative, voice pipeline diagram, RAG stack, and Dentrix integration surface: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**Short version:**
```
Wake word (Hey Jarvis / OpenWakeWord)
  → STT (Deepgram nova-2-medical)
  → Intent Router (Claude classifier)
  → Specialized Agent (one of 7)
  → ChromaDB RAG retrieval (30 evidence docs, 64 chunks)
  → Claude Sonnet response
  → TTS (ElevenLabs)
```

Production data layer: Dentrix via Henry Schein One LinkIt API (v1 uses mock).

---

## Demo Cases

Four mock cases demonstrate the multi-agent model end-to-end. See `data/mock_cases/`:

- **Case 1** ([case_01_crown_vs_composite](data/mock_cases/case_01_crown_vs_composite/)): AuditAgent flags a D2750 crown as likely overtreatment for a 30% occlusal caries lesion; recommends D2391 composite ($1,180 savings).
- **Case 2** ([case_02_endo_vs_extraction](data/mock_cases/case_02_endo_vs_extraction/)): AuditAgent + TreatmentCoordinatorAgent — flags missing endo option for tooth #8; TC script gives patient Options A and B with outcomes, timelines, and costs.
- **Case 3** ([case_03_perio_voice](data/mock_cases/case_03_perio_voice/)): PerioChartAgent converts hygienist's voice probe transcript into a structured periodontal chart with AAP 2017 Stage III, Grade B staging.
- **Case 4** ([case_04_lab_case_risk](data/mock_cases/case_04_lab_case_risk/)): LabCaseAgent scans 8 appointments for lab case risk — surfaces 3 critical, 1 at-risk; attributes the Robert Johnson case breakdown to a missing `lab_received` handoff step.

### Personas

| Persona | Role | Key JTBD | Agent |
|---|---|---|---|
| Maria, CDA | Dental Assistant | Chart without de-gloving | ChartAgent |
| Dr. Priya Patel | Associate Dentist (DSO) | Leave by 6pm; justify treatment | AuditAgent, DocumentationAgent, ResearchAgent |
| Karen | Treatment Coordinator | Present plans confidently in plain language | TreatmentCoordinatorAgent |
| Susan, RDH | Hygienist | Chart probe depths hands-free | PerioChartAgent |
| Diana Martinez | Front Desk Coordinator | Know lab case risks before patients arrive | LabCaseAgent |
| James | Patient | Understand if treatment is evidence-backed | AuditAgent |

---

## Stage 9 — Voice Demo

A standalone CLI that demonstrates the full voice-first activation loop without a browser.

### Install

```bash
# Voice deps are in requirements-local.txt (not the cloud-safe requirements.txt)
uv pip install -r requirements-local.txt
```

### Configure

```bash
cp .env.example .env
# Fill in:
#   ANTHROPIC_API_KEY   — Claude agent inference
#   DEEPGRAM_API_KEY    — speech-to-text (Nova-2 Medical)
#   ELEVENLABS_API_KEY  — text-to-speech
#   TTS_VOICE_ID        — ElevenLabs voice ID (optional; defaults to Rachel 21m00Tcm4TlvDq8ikWAM)
```

### Run

```bash
python -m scripts.voice_demo
```

**macOS microphone note:** On first run macOS will request microphone access. Approve it in
System Preferences → Privacy & Security → Microphone, then re-run.

### Example voice commands

Say **"Hey Jarvis"** to activate, then your command:

| Command | Agent |
|---|---|
| "Hey Jarvis — audit the crown versus composite case" | AuditAgent |
| "Hey Jarvis — scan tomorrow's lab cases" | LabCaseAgent |
| "Hey Jarvis — what does the AAE say about retreatment success rates?" | ResearchAgent |
| "Hey Jarvis — chart MO composite on tooth 14, A2 shade" | ChartAgent |
| "Hey Jarvis — tooth 3 distobuccal 4 buccal 3 mesiobuccal 5 bleeding mesial" | PerioChartAgent |

Full demo flow with expected spoken responses: [`scripts/voice_demo_examples.md`](scripts/voice_demo_examples.md)

### Notes

- Wake word is currently **"Hey Jarvis"** (OpenWakeWord pre-trained model). Training a custom **"Hey ToothTrust"** model
  is documented in [docs/IDEAS.md](docs/IDEAS.md) as a v2 task.
- Voice demo uses **ONNX runtime** for openWakeWord model inference. `onnxruntime` is included in
  `requirements.txt`. macOS users: if you see `tflite` import errors, run `pip install onnxruntime`
  — do **NOT** install `tflite-runtime`, which has poor macOS support.
- Required env vars: `ANTHROPIC_API_KEY` + `DEEPGRAM_API_KEY` + `ELEVENLABS_API_KEY`
- STT uses Deepgram **nova-2-medical** — optimised for clinical vocabulary.
- TTS responses are capped at **200 characters** spoken aloud; full structured output is logged to the terminal.

---

## Built with Claude Code

ToothTrust was built in 5 days using [Claude Code](https://claude.ai/code) — Anthropic's agentic CLI. Claude Code scaffolded the agent architecture, wrote and iterated on all 7 agents, generated the 30-document evidence corpus, built the RAG pipeline, designed the anti-hallucination guard test suite (42 tests), and polished the Streamlit demo UI across 10 staged builds. All 115 tests were written and validated with Claude Code.

---

## What I'd ship next

- **Patient Education Agent** — voice-triggered procedure video playback with timestamped consent logging; see [docs/IDEAS.md](docs/IDEAS.md)
- **XRayRecallAgent** — "pull up tooth 19" retrieves the correct radiograph on the operatory screen without touching a keyboard
- **PhasingAgent** — organizes flat treatment plan lists into Phase 1–4 with plain-language rationale for patients
- **PriorityAgent** — "what should we start today?" chairside decision support given available time and clinical constraints
