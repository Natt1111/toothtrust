# Feature Ideas

## Patient Education Agent

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

**Technical sketch (v2):**
- New agent: EducationAgent in src/agents/education_agent.py
- Video library: data/patient_education/ with metadata.json mapping CDT codes to videos
- Integration: starts as local video playback; v3 could integrate with Spear, DentalRAT, or DentalQuest libraries via API

**Data flywheel angle:** Track which videos patients actually watch end-to-end vs. skip. That telemetry tells dentists which education materials drive case acceptance.
