# ToothTrust

> Voice-first multi-agent platform for the dental office.

**[🦷 Live Demo → toothtrust.streamlit.app](https://toothtrust.streamlit.app/)**

---

## Run Locally

```bash
git clone https://github.com/Natt1111/toothtrust.git && cd toothtrust
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -r requirements.txt

cp .env.example .env   # fill in your keys — see below
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python streamlit run app/streamlit_app.py
```

Opens at `http://localhost:8501`. Four pages: **Overview**, **Voice Command**, **Case Studies**, **Platform**.

| Env var | Required for | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Case Studies (live runs), Voice Command | Without it, Case Studies falls back to **Sample Data Mode** — pre-validated results for all 4 cases, no key needed |
| `DEEPGRAM_API_KEY` | Voice Command | Speech-to-text (Nova-2 Medical). No fallback — voice is always a live pipeline |
| `ELEVENLABS_API_KEY` | Voice Command | Text-to-speech reply. Library voices (e.g. the default "Rachel") require a paid ElevenLabs plan — free-tier keys will transcribe fine but the spoken reply will silently skip |
| `APP_ACCESS_CODE` | optional | Gates Voice Command + all live (billed) Case Study runs behind a password prompt. Unset = no gate, for local dev. Sample Data Mode is never gated |

Each live agent call costs a few cents; a per-session cap (15 live calls) guards against runaway cost once deployed publicly.

Hosted on Streamlit Community Cloud → **[toothtrust.streamlit.app](https://toothtrust.streamlit.app/)**. `render.yaml` is included for deploying to [Render](https://render.com) instead (always-on, custom domain, no cold-start sleep) — connect the repo, add the four env vars above as dashboard secrets.

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
Activation: click-to-record (in-app) or wake word "Hey Jarvis" (CLI demo, OpenWakeWord)
  → STT (Deepgram nova-2-medical)
  → Intent Router (Claude classifier)
  → Specialized Agent (one of 7)
  → ChromaDB RAG retrieval (30 evidence docs, 64 chunks)
  → Claude Sonnet response
  → TTS (ElevenLabs)
```

Production data layer: Dentrix via Henry Schein One LinkIt API (v1 uses mock).

---

## Case Studies

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

## Voice Command (in-app)

The **Voice Command** page in the Streamlit app is the primary way to use voice — click to record in the browser (no wake word needed there — browsers won't allow a page to listen in the background, only after a click), and it runs the same live pipeline as the CLI demo below: Deepgram transcription → intent routing → the matching agent → an ElevenLabs spoken reply, with a running session transcript. Needs `ANTHROPIC_API_KEY`, `DEEPGRAM_API_KEY`, and `ELEVENLABS_API_KEY` — see the env var table above. There's no sample-data fallback for it; voice is always a live call.

A **🎙️ Voice Mode** toggle sits above the recorder: off by default (recorder hidden). Switch it on and the recorder stays ready — after each command's reply comes back, it auto-resets to a fresh empty recorder so you can tap-record the next command immediately, without first dismissing the previous clip. Not true hands-free (still one tap per command, per the browser mic constraint above), but it removes the extra click-to-clear step between commands.

---

## Stage 9 — CLI Voice Demo

A standalone CLI that demonstrates the full wake-word activation loop without a browser — useful for a hands-free, "Hey Jarvis" style demo distinct from the in-app Voice Command page above.

### Install

```bash
# Deepgram/ElevenLabs clients now ship in requirements.txt (used by the in-app
# Voice Command page too). requirements-local.txt adds the wake-word/mic-capture
# stack this CLI-only demo needs on top: sounddevice, openWakeWord, onnxruntime.
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
#                          note: library voices like Rachel need a paid ElevenLabs plan for API access —
#                          free-tier keys will transcribe fine but the spoken reply will fail
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
  `requirements-local.txt`. macOS users: if you see `tflite` import errors, run `pip install onnxruntime`
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
