# ADR-0004: LabCaseAgent as Complementary Layer to Dentrix Lab Case Manager

**Status**: Accepted  
**Date**: 2026-05-21  
**Deciders**: ToothTrust core team

---

## Context

Dentrix Lab Case Manager is a well-established module within Dentrix that allows practices to create lab cases from the Appointment Book or Patient Chart, track check-out and check-in, display an "L" icon on appointments with associated lab cases, and record expected return dates. Henry Schein One's DDX system further provides at-risk alerts when a case has a high probability of not returning before a scheduled appointment.

Henry Schein One launched **LinkIt** in August 2025 as an open-architecture API platform to streamline lab workflow integration across partner applications.

*(Sources: Dentrix Magazine, Henry Schein One product announcements — public sources only. No internal API documentation was referenced.)*

The question this ADR answers: **should ToothTrust build parallel lab case tracking infrastructure, or position LabCaseAgent as a proactive voice layer on top of Dentrix's existing data?**

---

## Decision

**LabCaseAgent is positioned as a complementary voice layer to Dentrix Lab Case Manager — not a replacement.**

It reads from and writes to the mock Dentrix interface in v1, with production integration designed for the Henry Schein One LinkIt API. It does not replicate Dentrix's tracking logic; it surfaces Dentrix's existing data proactively to the right staff member at the right time.

---

## The Actual Gap — Workflow Ownership, Not Feature Gaps

Dentrix Lab Case Manager already solves the tracking problem. The gap LabCaseAgent addresses is different:

**Dentrix requires active checking.** A front desk coordinator has to open Dentrix, navigate to Lab Case Manager, and review the list. In a practice managing 25–30 patients per day, this active check competes with phones, check-in/check-out, payment processing, and patient questions.

**The result:** lab case status is checked reactively — when the patient is already in the chair — rather than proactively the morning before. By then, reschedule options are limited, the patient is already present, and the clinical team's schedule is disrupted.

**LabCaseAgent converts active checking into passive notification.** A single morning voice command surfaces every at-risk case, triggers reschedule drafts for critical cases, and logs the "where did it fall through" handoff gap — all without opening Dentrix.

---

## Architectural Choice

| Layer | v1 (demo) | Production |
|---|---|---|
| Read appointments | `data/mock_data/appointments.json` | Henry Schein One LinkIt API |
| Read lab case status | `data/mock_data/lab_cases.json` | Henry Schein One LinkIt API |
| Write status update | Mutate local JSON (check-in) | POST to LinkIt API endpoint |
| Risk classification | Local deterministic logic | Same logic, live data |
| Reschedule drafts | Claude API (one call per patient) | Same |

All Dentrix references in v1 code are marked `MOCK INTERFACE` in docstrings. No Dentrix internal API endpoints, method names, or undocumented field structures are used or assumed.

---

## Trade-offs Accepted

**Tighter integration is more valuable than parallel infrastructure.** Building a second lab tracking system creates duplicate data entry burden for staff. Positioning as a voice layer on top of Dentrix means zero additional data entry: the data already lives in Dentrix Lab Case Manager; LabCaseAgent just surfaces it better.

**Risk: API access.** Henry Schein One controls access to the LinkIt API. If they restrict partner access or change pricing, ToothTrust's production integration would break.

**Mitigation:** The architecture is intentionally PMS-agnostic. The mock interface in v1 (`data/mock_data/`) can be replaced by any practice management system's API — Open Dental (open source), Eaglesoft (Patterson), or others. Risk classification and attribution logic are PMS-independent.

**Risk: DDX may add proactive notifications natively.** If Henry Schein One builds voice-accessible proactive scanning into DDX, LabCaseAgent's differentiation narrows.

**Mitigation:** LabCaseAgent's value is the voice layer and the cross-agent integration (e.g., handing off to TreatmentCoordinatorAgent to generate patient scripts). These are harder for a PMS vendor to replicate than raw notification logic.

---

## Consequences

- v1 demo runs entirely on local mock data — no Dentrix instance required for demonstration.
- Production integration path is clearly defined (LinkIt API) and requires partnership enrollment with Henry Schein One.
- Attribution analysis and risk classification are deterministic and testable without any external API calls.
- LabCaseAgent's system prompt explicitly uses the phrase "complementary to Dentrix Lab Case Manager" to reinforce positioning in all voice responses.
