# Voice of Customer

Synthesis of user research informing ToothTrust's product decisions.

---

## Primary Persona: Dental Assistant (Chairside)

**Name**: Maria, CDA  
**Context**: 6 years as a certified dental assistant in a 3-dentist group practice using Dentrix.

### Pain Points

> "Every time I need to chart something, I have to de-glove, type, re-glove. By the end of the day my hands are raw and I've broken sterile field a dozen times."

> "The doctor dictates findings but I'm the one who has to translate that into the right CDT code — and if I get it wrong, the claim gets denied."

> "I want to ask a quick question about a procedure mid-op but there's no good way to do it without stopping everything."

### Jobs to Be Done
1. Chart procedure findings and notes without touching a keyboard.
2. Look up the correct CDT code from a verbal description.
3. Get a quick answer to a clinical question ("is this contraindicated for patients on bisphosphonates?") without leaving the room.

### Success Metrics
- De-gloving events per day: target < 2 (from ~12)
- CDT coding accuracy: target > 95%
- Time from finding → chart entry: target < 10 seconds

---

## Secondary Persona: Dental Patient (Second Opinion Seeker)

**Name**: James, 52  
**Context**: Was quoted $4,200 for a full-arch treatment plan. Wants to understand whether each procedure is justified before committing.

### Pain Points

> "My dentist said I need three crowns and a deep cleaning. I have no idea if that's right or if he's just upselling me."

> "I Googled it but I couldn't tell what was legitimate information and what was marketing."

> "I wish someone could just tell me: here's what the evidence says, here's whether your specific X-rays support this recommendation."

### Jobs to Be Done
1. Understand whether each proposed procedure is evidence-backed.
2. Get a plain-language explanation of the clinical rationale.
3. Know what questions to ask at the follow-up appointment.

### Success Metrics
- Patient confidence score (post-report survey): target > 4/5
- "Would recommend to a friend": target > 80%
- Reduction in "I need a second opinion" appointment cancellations for the practice

---

## Persona: Associate Dentist (DSO)

**Name**: Dr. Priya Patel, DDS  
**Context**: Age 38, 9 years in practice, associate at a DSO running Dentrix. Sees 24–28 patients/day across two operatories.

### Pain Points

> "I'm strong clinically but I'm drowning in documentation. I stay 60–90 minutes after my last patient almost every day."

> "I want to show patients exactly what's going on with their tooth, but pulling up the right X-ray mid-conversation means walking to the computer and clicking through three menus — while they're watching me."

> "Every treatment plan I present, insurance wants justification. I know the clinical rationale, but writing it up for each claim takes time I don't have."

### Jobs to Be Done (ordered by urgency)
1. **Leave the office by 6pm without taking documentation home** — #1 JTBD.
2. Show patients procedures visually without leaving the operatory.
3. Pull up specific X-rays during patient conversations.
4. Phase complex treatment plans clearly so patients understand what comes first and why.
5. Decide chairside what to prioritize today vs. next visit based on time and clinical logic.
6. Justify treatment plans with evidence that both patients and insurance accept.

### ToothTrust Value
- **DocumentationAgent** (v1): SOAP draft → voice review → voice sign eliminates after-hours documentation.
- **EducationAgent** (v2): voice-triggered procedure videos on the operatory screen.
- **XRayRecallAgent** (v2): "Pull up tooth 19" retrieves the correct image without keyboard interaction.
- **PhasingAgent** (v2): organizes treatment plans into Phase 1–4 automatically.
- **PriorityAgent** (v2): "What should we start today?" considers time, anesthesia, and healing requirements.
- **ResearchAgent** (v1): chairside evidence for clinical questions and insurance justification language.

### ROI Signal
> "If our 500 DSO dentists save 60 minutes/day on documentation, that's 500 hours/day of dentist time recovered." — DSO operations director framing for procurement conversations.

---

## Persona: Treatment Coordinator

**Name**: Karen  
**Context**: 8 years in the role, started at the front desk, now handles case presentation. Makes 6–10 treatment plan presentations daily across all three dentists in the practice.

### Pain Points

> "The doctor hands me a treatment plan and expects me to explain it to the patient. But I don't have clinical training — I'm basically improvising."

> "Patients ask me 'what does a crown involve?' or 'what happens if I just wait?' and I don't always have a confident answer."

> "When a patient declines treatment I feel like it's my fault, but I never know if I explained it wrong or if the price was just too high."

### Jobs to Be Done
1. Present treatment plans to patients in plain language without clinical training.
2. Answer "what does this involve?" without sounding uncertain or reading from a pamphlet.
3. Increase case acceptance without overselling or making promises the dentist can't keep.
4. Document patient questions and objections for the dentist's follow-up.

### ToothTrust Value
- **TreatmentCoordinatorAgent** (v1): translates the clinical audit result into a patient-conversation script with plain-language explanations, each option's worst-case scenario, typical outcomes, timelines, costs, and a recommended framing — not a hard sell.

---

## Persona: Dental Hygienist (RDH)

**Name**: Susan  
**Context**: 12 years as a registered dental hygienist. Performs 8–10 perio exams and full-mouth debridements per day. Currently relies on an assistant to scribe probe depths during exams.

### Pain Points

> "I have to call out every number and then watch the assistant type it in and hope they got it right. If they're pulled away for something else, I'm stuck."

> "AAP staging requires me to calculate the worst CAL across the whole mouth and then remember the criteria. I know them, but after 10 patients I've done the math wrong."

> "I want to keep two hands on the patient and my eyes in the mouth. Having a scribe means breaking someone else's workflow too."

### Jobs to Be Done
1. Chart periodontal probing without breaking patient contact or borrowing another staff member.
2. Get AAP 2017 staging and grading automatically from probe data — no manual calculation.
3. Document bleeding on probing, recession, and mobility hands-free.

### ToothTrust Value
- **PerioChartAgent** (v1): transcribes voice probe calls ("tooth 3 distobuccal 4 buccal 3 mesiobuccal 5 bleeding") into a structured periodontal chart, computes clinical attachment loss per site, and returns AAP 2017 stage and grade with recommended next steps.

---

## Persona: Front Desk Coordinator

**Name**: Diana Martinez  
**Context**: 6 years in front desk roles. Manages 30+ appointments per day — answers phones, processes payments, handles check-in and check-out, and coordinates between clinical staff and patients.

### Pain Points

> "I forget to check lab cases until the patient is already here."

### Jobs to Be Done
1. Know which lab cases are at risk for tomorrow without having to manually look through Dentrix Lab Case Manager.
2. Quickly check a single case status by voice while on the phone with a patient — without putting them on hold to navigate to a screen.
3. Get reschedule messages drafted automatically when a case won't arrive in time.
4. Know which step in the workflow broke when something falls through — without guessing or asking around.

### ToothTrust Value
- **LabCaseAgent** (v1): proactively scans tomorrow's schedule for lab case risk, surfaces critical/at-risk appointments, identifies handoff gaps, and drafts patient reschedule messages — all via a single morning voice command.

---

## Key Insights for Product

1. **Hands-free is non-negotiable for chairside** — push-to-talk is not enough; wake-word activation is required.
2. **Speed matters more than comprehensiveness** — a 3-second voice response beats a 15-second comprehensive answer mid-procedure.
3. **Patients want citations, not conclusions** — "the ADA recommends..." is more trustworthy than "you should...".
4. **The practice's workflow is the distribution channel** — if the assistant loves it, the dentist sees the value; patient-facing features are secondary.
5. **Fear of liability shapes everything** — every recommendation must be framed as informational, not prescriptive.
6. **Every role has the same hands-busy problem** — gloved hands, patient contact, and workflow continuity block every staff member from accessing information; the voice layer is the universal unlock.
7. **DSO buyers need platform ROI, not feature ROI** — individual agents solve individual problems, but the DSO procurement conversation requires demonstrating time saved across the full staff roster.
