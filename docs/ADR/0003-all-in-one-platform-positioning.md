# ADR-0003: Expand from Single-Purpose Audit Tool to Voice-First Multi-Agent Platform

**Status**: Accepted  
**Date**: 2026-05-20  
**Deciders**: ToothTrust core team

---

## Context

ToothTrust launched as a single-purpose tool: a voice-activated treatment plan auditor that retrieves dental evidence and flags potential overtreatment. The original scope served one user (the patient seeking a second opinion) with one workflow (audit → report).

Two things triggered a re-evaluation of that scope:

**1. Real-world workflow analysis revealed that every staff role in a dental office has the same core problem.** The gloved-hands constraint isn't unique to the charting assistant. Hygienists calling out probe depths, treatment coordinators presenting plans, and dentists dictating notes all need hands-free access to information and documentation. The voice + AI layer solves the same problem for every role — the agents just differ.

**2. Competitive analysis of VideaHealth exposed workflow gaps that diagnostic imaging AI doesn't address.** VideaHealth, Pearl, and Overjet all solve the imaging interpretation problem well. None of them address chairside documentation, treatment coordinator scripting, or periodontal charting. The market has diagnostic AI; it does not have a workflow AI layer for the full dental office team.

---

## Decision

Expand ToothTrust to a **voice-first multi-agent platform serving all four dental office roles** (clinical assistant, hygienist, treatment coordinator, dentist), with **six agents shipped in v1** and **four additional agents specified and designed for v2**.

### v1 Agents (shipping)

| Agent | Target User | Core Job |
|---|---|---|
| ChartAgent | Dental Assistant | Voice → structured chart entry + CDT code |
| AuditAgent | Dentist / Patient | Treatment plan audit with evidence citations |
| ResearchAgent | Any clinical staff | Chairside RAG question answering |
| DocumentationAgent | Dentist | Ambient SOAP note draft → voice review → sign |
| TreatmentCoordinatorAgent | Treatment Coordinator | Audit result → patient-conversation script |
| PerioChartAgent | Hygienist | Voice probe calls → structured perio chart + AAP staging |

### v2 Agents (designed, not built until v1 ships)

| Agent | Target User | Core Job |
|---|---|---|
| EducationAgent | Any staff | Voice-triggered procedure video on operatory screen |
| XRayRecallAgent | Dentist | "Pull up tooth 19" → opens correct radiograph |
| PhasingAgent | Dentist / TC | Organizes treatment plan into Phase 1–4 |
| PriorityAgent | Dentist | "What should we start today?" given time and context |

---

## Rationale

**DSO buyers need platform-level value.** A single-purpose audit tool competes as a feature. A multi-agent platform that serves every staff member competes as infrastructure. DSO procurement evaluates tools by time-saved-per-staff-member-per-day across the full roster. The platform positioning unlocks that ROI calculation: 500 dentists × 60 min/day on documentation = 500 hours/day recovered.

**Individual agents are intentionally narrow.** The risk of a multi-agent platform is that agents become bloated and unreliable. Each agent in ToothTrust has a single, tightly scoped job. System prompts are short and specific. Output schemas are validated. Narrow agents are easier to test, easier to explain to users, and easier to tune.

**The voice and orchestration layer is the shared infrastructure.** Every agent uses the same wake-word pipeline, intent router, and ChromaDB retrieval stack. Adding a new agent is additive — it doesn't touch the existing agents. The platform architecture makes each new agent cheaper to build than the last.

**Complementary to diagnostic AI, not competitive.** VideaHealth, Pearl, and Overjet identify pathology from X-rays. ToothTrust takes that diagnosis and helps staff act on it — chart it, audit the resulting treatment plan, explain it to the patient, document it. The positioning is "what happens after the AI finds something" rather than "finding the thing."

---

## Trade-offs Accepted

**More surface area to maintain.** Six agents in v1 is more code than one. Mitigation: each agent is ~50 lines of Python; the shared base class and retrieval layer do the heavy lifting. Test coverage is mandatory for each agent.

**Risk of feature bloat in v2.** Four v2 agents are specified but not built. The explicit v1/v2 cut enforces discipline. v2 agents do not get built until v1 ships and real-user feedback validates the demand.

**Orchestration complexity increases with agent count.** The intent router must correctly classify more utterance types as the agent count grows. Mitigation: the router uses Claude with an explicit classification prompt; adding a new intent requires one line in the enum and one entry in the system prompt. Regression testing on existing intents is required before each new agent ships.

**Each agent has its own system prompt surface for hallucination.** More prompts = more potential for subtle prompt drift over model versions. Mitigation: each agent's system prompt is tested with fixed mock outputs; prompt changes require tests to pass.

---

## Validation Plan

- **3 demo cases** prove the multi-agent model: Case 1 (AuditAgent), Case 2 (AuditAgent + TreatmentCoordinatorAgent), Case 3 (PerioChartAgent). See `data/mock_cases/`.
- **v2 features are designed but gated**: all four v2 agents have full specs in `docs/IDEAS.md`. No v2 code is merged until v1 demo cases ship and at least one practice provides validation feedback.
- **Success signal for platform pivot**: a practice manager or DSO operations lead references more than two agents in the same sentence when describing ToothTrust's value.
