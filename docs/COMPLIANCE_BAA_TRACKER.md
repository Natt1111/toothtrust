# HIPAA BAA Tracker — Anthropic, Deepgram, ElevenLabs

**Status**: In Progress — research done, outreach not yet sent
**Date opened**: 2026-07-21
**Owner**: Natthaporn Gulgalkhai
**Blocks**: Milestone 2 in [docs/PRODUCTION_PATH.md](PRODUCTION_PATH.md) — no real patient data may reach any of these three vendors until its row below is ✅.

---

## Why this exists

Every live voice command sends content to three outside AI vendors: Anthropic (Claude), Deepgram (STT), ElevenLabs (TTS). Under HIPAA, none of them may receive real PHI until a signed Business Associate Agreement (BAA) is in place. This is a legal/vendor process on their timeline, not engineering — tracked here separately from the code-shaped items in `PRODUCTION_PATH.md` so it doesn't get lost between "waiting on a reply" and "actually done."

**Sample Data Mode and the demo/pitch flow are unaffected** — this only gates the day real patient data starts flowing through the app.

---

## Status table

| Vendor | Eligible path | Requirements | Contact | Status |
|---|---|---|---|---|
| **Anthropic** | First-party API — "HIPAA-Ready API Org" (ToothTrust already calls `anthropic.Anthropic()` directly, so this is the right path, not Claude Enterprise) | Primary Owner signs Anthropic's BAA, then Anthropic Sales activates it on the org. Covered models require **30-day data retention** — cannot combine with zero-data-retention. | [claude.com/contact-sales](https://claude.com/contact-sales) | ⬜ Not started |
| **Deepgram** | BAA available on request, any qualifying plan | Contact their Account Executive / sales team directly to request the BAA paperwork | Deepgram sales / support | ⬜ Not started |
| **ElevenLabs** | **Enterprise tier only** — the plan upgrade already made ("i paid elevenlabs") almost certainly is *not* Enterprise, so this is very likely still blocked even post-upgrade | BAA **and** Zero Retention Mode must both be enabled — Zero Retention auto-deletes audio in/out after each request | ElevenLabs Sales | ⬜ Not started — **check current plan tier first, before assuming the recent upgrade covers this** |

---

## Outreach drafts — ready to send as-is

### Anthropic

> Subject: BAA request — HIPAA-Ready API Org
>
> Hi Anthropic team,
>
> I'm building ToothTrust, a voice-first clinical copilot for dental offices, using the first-party Claude API (`anthropic.Anthropic()` client, not Console/Workbench). Ahead of our first pilot practice, I need to put a Business Associate Agreement in place so we can process real patient-derived content through the API.
>
> Could you point me to the process for signing a BAA on the API org, and let me know if there's a minimum usage tier or other prerequisite before it can be activated?
>
> Thanks,
> [name]

### Deepgram

> Subject: BAA request for HIPAA-eligible use
>
> Hi Deepgram team,
>
> We use the Deepgram API (nova-2-medical model) for speech-to-text in ToothTrust, a dental office voice copilot. We're preparing for our first real-patient pilot and need a signed Business Associate Agreement before any real patient audio is sent to the API.
>
> Could you send over your standard BAA and let me know if there's a specific plan tier required?
>
> Thanks,
> [name]

### ElevenLabs

> Subject: BAA + Zero Retention Mode — plan requirements
>
> Hi ElevenLabs team,
>
> We use the ElevenLabs API for text-to-speech in ToothTrust, a dental office voice copilot, currently on [plan name]. I understand HIPAA support requires both a signed BAA and Zero Retention Mode, and that this is only available on the Enterprise tier.
>
> Could you confirm whether our current plan qualifies, and if not, what the upgrade path and pricing look like for Enterprise with Zero Retention Mode enabled?
>
> Thanks,
> [name]

---

## Next action

1. Check the actual ElevenLabs plan tier from the last upgrade — if it isn't Enterprise, the BAA path isn't open yet regardless of outreach.
2. Send the three drafts above (fill in `[name]` / `[plan name]`).
3. Update the status table as replies come in — this file is the single source of truth for where each conversation stands.
