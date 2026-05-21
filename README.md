# ToothTrust

> Voice-first multi-agent platform for the dental office.

---

## Live Demo

```bash
# Quick start (requires Python 3.11 + uv)
git clone https://github.com/Natt1111/toothtrust.git && cd toothtrust
uv venv --python 3.11 && source .venv/bin/activate
uv pip install streamlit chromadb sentence-transformers anthropic pypdf python-dotenv pandas \
  "numpy<2" "torch==2.1.2" "chromadb==0.5.23" "protobuf>=3.20,<4"
cp .env.example .env   # add your ANTHROPIC_API_KEY
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python streamlit run app/streamlit_app.py
```

Opens at `http://localhost:8501`. Each "Run Audit" click costs ~$0.05. Results are cached in session.  
Works in **offline mode** (no API key) — shows pre-computed results for all 3 cases.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Streamlit Community Cloud deployment.

---

## Problem

ToothTrust is a voice-first multi-agent platform for the dental office. Every staff role — assistant, hygienist, treatment coordinator, dentist — has a specialized AI copilot that works hands-free through voice commands.

The core problem: dental staff are always busy with their hands. Gloves, instruments, patient contact. Every time someone needs to look something up, chart a finding, explain a procedure, or document a visit, they have to stop what they're doing. That friction compounds across 20+ patients a day per provider.

The voice layer removes that friction for every role. The agent layer gives each role the specific AI capability they need.

---

## Agent Platform

### v1 — Shipping

| Agent | Target User | Voice Command Example | Core Job |
|---|---|---|---|
| ChartAgent | Dental Assistant | "Chart MOD composite on 19" | Voice → structured chart entry + CDT code |
| AuditAgent | Dentist / Patient | "Is this crown justified?" | Treatment plan audit with evidence citations |
| ResearchAgent | Any clinical staff | "Bisphosphonate contraindications?" | Chairside RAG question answering |
| DocumentationAgent | Dentist | "Draft the note" / "Sign it" | Ambient SOAP note draft → voice review → sign |
| TreatmentCoordinatorAgent | Treatment Coordinator | "Explain this to the patient" | Audit result → plain-language patient script |
| PerioChartAgent | Hygienist | "Tooth 3 distobuccal 4 buccal 3..." | Voice probe calls → structured perio chart + AAP staging |

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

<!-- TODO: Diagram + narrative covering voice pipeline, RAG stack, agent layer, Dentrix integration surface. -->

---

## Demo Cases

Three mock cases demonstrate the multi-agent model end-to-end. See `data/mock_cases/`:

- **Case 1** ([case_01_crown_vs_composite](data/mock_cases/case_01_crown_vs_composite/)): AuditAgent flags a D2750 crown as likely overtreatment for a 30% occlusal caries lesion; recommends D2391 composite ($1,180 savings).
- **Case 2** ([case_02_endo_vs_extraction](data/mock_cases/case_02_endo_vs_extraction/)): AuditAgent + TreatmentCoordinatorAgent — flags missing endo option for tooth #8; TC script gives patient Options A and B with outcomes, timelines, and costs.
- **Case 3** ([case_03_perio_voice](data/mock_cases/case_03_perio_voice/)): PerioChartAgent converts hygienist's voice probe transcript into a structured periodontal chart with AAP 2017 Stage II, Grade B staging.

---

## Setup

<!-- TODO: Clone, copy .env.example, pip install, run the Streamlit app or FastAPI server. -->

---

## Built with Claude Code

<!-- TODO: Describe how Claude Code was used to scaffold, iterate, and review the codebase. -->

---

## What I'd ship next

- **Patient Education Agent** — voice-triggered procedure video playback with timestamped consent logging; see [docs/IDEAS.md](docs/IDEAS.md)
- **XRayRecallAgent** — "pull up tooth 19" retrieves the correct radiograph on the operatory screen without touching a keyboard
- **PhasingAgent** — organizes flat treatment plan lists into Phase 1–4 with plain-language rationale for patients
- **PriorityAgent** — "what should we start today?" chairside decision support given available time and clinical constraints
