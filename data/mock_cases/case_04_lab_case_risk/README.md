# Case 04 — Lab Case Risk Scanner

**Demo scenario:** It's Monday 7am. Diana (Front Desk Coordinator) opens ToothTrust to scan tomorrow's schedule for lab case risks before the clinical day starts.

**Agent:** LabCaseAgent (v1 — mock Dentrix interface; production uses Henry Schein One LinkIt API)

---

## Demo Flow

### Step 1 — Morning scan
Diana says: *"Hey ToothTrust, scan tomorrow's lab cases."*

`LabCaseAgent.scan_tomorrows_appointments()` cross-references `appointments.json` with `lab_cases.json` and returns:
- **2 on track** (Sarah Chen, James Rodriguez)
- **1 at risk** (Michael Thompson — expected return is after the appointment date)
- **3 critical** (David Kim — overdue no update; Maria Gonzalez — in transit with <48h to appt; Robert Johnson — no lab update since sent)
- **2 no case required** (Linda Patel, Patricia Lewis — no lab case needed)

Expected output: `expected_scan_output.json`

### Step 2 — Single case lookup
Diana: *"Hey ToothTrust, where's the Chen case?"*

`LabCaseAgent.lookup_case('Sarah Chen')` returns: shipped back from Glidewell, expected delivery today, appointment tomorrow — on track.

Expected output: `expected_lookup_output.json`

### Step 3 — Attribution ("where did it fall through?")
For the Robert Johnson critical case, Diana asks: *"Where did the Johnson case fall through?"*

`LabCaseAgent.attribution_check('LC-4406')` identifies:
- Last completed step: `sent_to_lab` (2026-05-08)
- Broken step: `lab_received` — no receipt confirmation was ever recorded
- Responsible role: Dental Lab
- Suggested fix: Contact lab to confirm receipt; add tracking numbers to future outbound shipments

Expected output: `expected_attribution_output.json`

---

## Key Design Decisions

- **All outputs are deterministic** — no LLM call for scan, lookup, or attribution. Only `recommend_reschedules()` calls Claude (to draft patient messages).
- **Complementary to Dentrix Lab Case Manager** — not a replacement. Surfaces existing data proactively.
- **Attribution frames workflow gaps, never individual blame.** See `framing_note` in attribution output.
- **Mock interface clearly marked** — production uses Henry Schein One LinkIt API.
