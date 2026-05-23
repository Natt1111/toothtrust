# Feature Ideas

> **Note**: LabCaseAgent was originally considered for v2 but has been promoted to **v1** and fully implemented in `src/agents/lab_case_agent.py`. See `docs/ADR/0004-lab-case-agent-positioning.md`.

---

## Custom "Hey ToothTrust" Wake Word Model (v2)

**Trigger:** Replace the current `alexa` placeholder wake word with a branded activation phrase
that reinforces the product name and reduces false positives.

**Behavior:** openWakeWord supports training custom wake word models from recorded audio samples.
A trained `hey_toothtrust_v1.tflite` model file would be dropped into
`data/wake_word_models/` and loaded at startup via
`Model(wakeword_models=["data/wake_word_models/hey_toothtrust_v1.tflite"])`.

**Why this matters:**
- "Alexa" is a household wake word — high false-positive rate in any home or mixed-use environment.
- A custom model is harder to accidentally trigger and creates a stronger product identity.
- Clinicians build trust faster with voice products that respond only to intentional activations.

**Training sketch:**
1. Record ~10 minutes of "Hey ToothTrust" samples from multiple speakers (different accents, distances, noise levels).
2. Use the openWakeWord training pipeline (`openwakeword.train`) with the recorded samples + negative examples.
3. Export as a `.tflite` model file and evaluate false-positive rate on a hold-out set.
4. Drop the model file into `data/wake_word_models/` and set `WAKE_WORD_MODEL_PATH` in `.env`.
   The `_build_demo()` factory in `scripts/voice_demo.py` reads this path automatically.

**Required samples:** ~300–500 positive utterances from 5–10 speakers; standard desktop recording environment is sufficient for v1.

---

## Patient Education Agent (v2)

**Trigger:** Voice command from clinician or front desk staff (e.g., "Hey ToothTrust, show this patient the crown procedure video")

**Behavior:** The agent identifies the relevant procedure from the voice command (mapped to CDT code if possible), opens the appropriate patient education video on the chairside or operatory screen, and verbally confirms ("Now playing: crown procedure overview, 90 seconds")

**Use cases:**
- Patient asks "what does that involve?" → assistant says "Hey ToothTrust, show the [procedure] video"
- Front desk pre-appointment education
- Informed consent documentation — agent can log "patient was shown D2750 procedure video at 2:14 PM" to the chart

**Why this matters:**
- Solves the same gloved-hands problem as ChartAgent — staff don't have to break workflow to find videos
- Improves informed consent documentation (timestamped video views in chart)
- Increases case acceptance — patients who see what a procedure involves are more likely to accept treatment
- Differentiates from VideaHealth's patient education panel (currently click-based, not voice-driven)

**Technical sketch:**
- New agent: `EducationAgent` in `src/agents/education_agent.py`
- Video library: `data/patient_education/` with `metadata.json` mapping CDT codes to videos
- Integration: starts as local video playback; v3 could integrate with Spear, DentalRAT, or DentalQuest libraries via API

**Data flywheel angle:** Track which videos patients actually watch end-to-end vs. skip. That telemetry tells dentists which education materials drive case acceptance.

---

## XRayRecallAgent (v2)

**Trigger:** "Pull up tooth 19" / "Show me all bitewings from this year"

**Behavior:** Parses the voice command to identify tooth number, X-ray type, and date range. Opens the correct radiograph on the operatory screen and highlights the specified tooth if the imaging system supports overlays. Verbally confirms: "Showing periapical for tooth 19, taken March 2025."

**Use cases:**
- Chairside patient explanation — dentist can show the patient exactly what they're looking at without leaving the conversation
- Quick reference between operatories without walking to a workstation
- Treatment planning — "show me all crowns from the last 5 years" for full-arch cases

**Why this matters:**
- Pulling up X-rays mid-conversation currently requires breaking patient rapport to reach a mouse and keyboard
- Patients who see their own X-ray during the explanation are more likely to accept treatment and trust the recommendation
- Reduces time per patient conversation by 2–3 minutes in complex cases

**Technical sketch:**
- New agent: `XRayRecallAgent` in `src/agents/xray_recall_agent.py`
- v1: Dentrix imaging API mock (`src/integrations/dentrix_mock.py`) returning fixture image paths
- Production: Henry Schein One partner API or Dentrix Enterprise Imaging API (requires NDA + integration agreement)
- Output: `{"tooth": 19, "xray_type": "periapical", "image_path": "...", "date": "2025-03", "action": "open_on_screen"}`

**Data flywheel angle:** Log which X-rays are pulled during patient conversations. High-frequency recalls on specific teeth correlate with treatment acceptance decisions — useful for case outcome analytics.

---

## PhasingAgent (v2)

**Trigger:** "Phase this treatment plan" (after AuditAgent has evaluated a plan, or with a raw treatment plan as input)

**Behavior:** Organizes treatment plan items into the standard four clinical phases, with plain-language labels and rationale for each phase's sequencing:

- **Phase 1 — Urgent / Disease Control**: active caries, infections, acute pain, extractions of hopeless teeth
- **Phase 2 — Restorative**: fillings, crowns, root canal treatment (after disease control is complete)
- **Phase 3 — Definitive**: implants, bridges, orthodontics, cosmetic procedures (after restorative stability)
- **Phase 4 — Maintenance**: recall cleanings, periodontal maintenance, annual X-rays

**Use cases:**
- Treatment coordinators presenting long plans to patients: "Here's what we do first and why"
- Dentists ordering their own thought process for complex cases
- Insurance justification: phased plans reduce sticker shock and show clinical logic

**Why this matters:**
- Real dentists think and plan in phases; Dentrix displays treatment plans as flat lists with no inherent sequencing
- Patients presented with a phased plan have a clearer mental model and fewer objections about cost ("we don't do everything at once")
- Junior associates benefit most — phasing logic is a clinical skill that takes years to develop intuitively

**Technical sketch:**
- New agent: `PhasingAgent` in `src/agents/phasing_agent.py`
- Input: list of procedures (from AuditAgent result or raw) + patient context
- Output: structured JSON with procedures grouped by phase, each with rationale
- Claude prompt instructs phasing using ADA sequencing principles; no hardcoded rules

**Data flywheel angle:** Track which phases patients accept vs. defer. Phase 3 deferral rates by procedure type reveal which elective treatments have the weakest case acceptance — actionable for practice growth.

---

## PriorityAgent (v2)

**Trigger:** "What should we start today?" — called after PhasingAgent has organized the plan, with appointment context available (scheduled time, existing anesthesia from prior visit, post-op healing constraints)

**Behavior:** Analyzes the phased treatment plan against today's appointment context and recommends the optimal set of procedures for the current visit vs. which to schedule next. Outputs a plain-language recommendation with clinical rationale.

**Example output:**
> "Patient is here for 60 minutes. I recommend SRP upper right and upper left today — both quadrants share anesthesia, and leaving lower quadrants for a separate visit avoids bilateral numbness. Schedule lower right and lower left together in 3–4 weeks."

**Use cases:**
- Chairside decision support at the start of a visit: "we have 45 minutes, what's the priority?"
- Turns junior associates into more senior clinical decision-makers
- Reduces chair time waste from under-planning (doing too little) or over-scheduling (running over)

**Why this matters:**
- Experienced dentists make this judgment intuitively in 30 seconds; new associates often under-treat or over-treat a single appointment
- Anesthesia sharing, healing sequencing, and patient tolerance are real constraints that Dentrix scheduling ignores
- DSO value: maximizing revenue-per-appointment-hour is a key operations metric

**Technical sketch:**
- New agent: `PriorityAgent` in `src/agents/priority_agent.py`
- Input: phased plan (from PhasingAgent) + `appointment_minutes`, `existing_anesthesia`, `last_visit_date`
- Output: `{"today": [...procedures], "next_visit": [...procedures], "rationale": "..."}`
- Claude prompt trained on appointment optimization heuristics; v2 could incorporate historical timing data per procedure type

**Data flywheel angle:** Track predicted vs. actual appointment duration. Systematic over/underestimates by procedure type improve the model's timing heuristics over time.
