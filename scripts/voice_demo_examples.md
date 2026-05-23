# Voice Demo — Example Commands

Use these commands during a recorded demo. Say **"alexa"** (the v1 placeholder wake word)
followed immediately by the command below.

---

## 1 — AuditAgent

**Voice command:**
> "Alexa — audit the crown versus composite case"

**Expected agent route:** `AuditAgent` (intent: `audit`)

**Spoken response (first ~200 chars):**
> "This treatment plan is partially supported. The D2750 crown has moderate evidence; however, a D2391 composite may be appropriate given 30% occlusal involvement. I'd recommend confirming caries extent with…"

---

## 2 — LabCaseAgent

**Voice command:**
> "Alexa — scan tomorrow's lab cases"

**Expected agent route:** `LabCaseAgent` (intent: `lab_case`, fast-path regex)

**Spoken response (first ~200 chars):**
> "Scanning tomorrow's schedule. I found 3 appointments with lab cases. 2 are critical: the Johnson crown is overdue and has no lab_received confirmation. The Martinez bridge is on track. 1 case is…"

---

## 3 — ResearchAgent

**Voice command:**
> "Alexa — what does the AAE say about retreatment success rates?"

**Expected agent route:** `ResearchAgent` (intent: `research`)

**Spoken response (first ~200 chars):**
> "According to the AAE, non-surgical endodontic retreatment has reported success rates of 74–77% at 4 years. Factors influencing outcomes include initial periapical lesion size, coronal seal quality, and…"

---

## 4 — ChartAgent

**Voice command:**
> "Alexa — chart MO composite on tooth 14, A2 shade"

**Expected agent route:** `ChartAgent` (intent: `chart`)

**Spoken response (first ~200 chars):**
> "Charted: D2392 composite resin, MO, tooth 14, shade A2. Entry added to today's chart."

---

## 5 — PerioChartAgent

**Voice command:**
> "Alexa — tooth 3 distobuccal 4 buccal 3 mesiobuccal 5 bleeding mesial"

**Expected agent route:** `PerioChartAgent` (intent: `perio_chart`, fast-path regex)

**Spoken response (first ~200 chars):**
> "Recorded tooth 3: distobuccal 4, buccal 3, mesiobuccal 5 with bleeding on probing at the mesial site. Preliminary staging suggests localized Stage II. Continue charting or say 'done' to finalize."

---

## Demo flow tips

- Run `python -m scripts.voice_demo` in one terminal; keep a second terminal open for logs.
- Each command prints the raw transcript, the agent route, and the first 200 chars of the response — useful for screen recordings.
- Full structured output (procedures, CDT codes, citations) is visible in the terminal log even though only the first 200 chars are spoken aloud.
- For the AuditAgent and LabCaseAgent commands, the demo cases in `data/mock_cases/` produce consistent responses regardless of live Anthropic API non-determinism — good for repeatable recordings.

---

## Notes

- **Wake word:** `alexa` is a placeholder. See `docs/IDEAS.md` for the v2 plan to train a custom "Hey ToothTrust" wake word model.
- **TTS voice:** Set `TTS_VOICE_ID` in `.env` to your preferred ElevenLabs voice ID. Defaults to Rachel (`21m00Tcm4TlvDq8ikWAM`).
- **STT model:** Deepgram `nova-2-medical` — optimised for clinical vocabulary, handles dental procedure names accurately.
