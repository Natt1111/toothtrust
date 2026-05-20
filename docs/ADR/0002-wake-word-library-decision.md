# ADR-0002: Wake Word Library — openWakeWord over Picovoice Porcupine

**Status**: Accepted  
**Date**: 2026-05-20  
**Deciders**: ToothTrust core team  
**Supersedes**: Initial selection of Picovoice Porcupine in scaffold

---

## Context

ToothTrust's voice pipeline requires always-on, on-device wake word detection so clinicians can activate the assistant hands-free while gloved at chairside. The initial scaffold used **Picovoice Porcupine** (`pvporcupine`) for this role.

During environment setup, Picovoice's free tier was found to no longer be self-serve. New free-tier access requires submitting an enterprise trial request through their sales pipeline — an access model incompatible with rapid open-source prototyping and with the project's goal of frictionless contributor onboarding.

Additionally, a dental AI product positioning toward HIPAA compliance benefits from a wake word stack where: (a) no audio or telemetry leaves the device during detection, and (b) the dependency has no licensing terms that could complicate a Business Associate Agreement (BAA).

---

## Alternatives Considered

### 1. Picovoice Porcupine — *original choice, rejected going forward*
- **Pros**: Excellent accuracy; tiny on-device footprint; pre-trained "Hey Siri"-style models; iOS/Android SDKs for a future companion app.
- **Cons**: Free tier is now gated behind a sales-mediated enterprise trial request; commercial use requires a paid license ($0.001/activation or subscription); access key required at runtime means every developer needs individual provisioning; less favorable narrative for a HIPAA-adjacent product where third-party key dependencies raise questions during audits.

### 2. Picovoice Foundation (open-source fork)
- **Pros**: Open-source subset of Porcupine maintained by the community.
- **Cons**: Smaller model selection; not officially supported by Picovoice; custom wake word training requires their proprietary console even for the open fork; maintenance uncertainty.

### 3. openWakeWord — *selected*
- **Pros**: Fully open-source (Apache 2.0); no API key; no network calls during inference; pre-trained models included (`hey_jarvis`, `alexa`, `hey_mycroft`, and others); custom wake word training is entirely local using open tools (speech synthesis + model training pipeline provided in the repo); active community; designed explicitly for privacy-preserving on-device use.
- **Cons**: Pre-trained model vocabulary is smaller than Porcupine's; custom "hey tooth trust" model requires running the openWakeWord training pipeline (speech synthesis → augmentation → fine-tuning) — more manual than Porcupine's cloud console; slightly higher CPU usage than Porcupine's highly optimized C engine.

### 4. Snowboy (PrecisionOS)
- **Pros**: Was historically popular for on-device detection.
- **Cons**: Project is effectively abandoned (last commit 2020); Python 3.11 compatibility is broken; not viable.

---

## Decision

Replace `pvporcupine` with **openWakeWord**.

The `WakeWordDetector` public interface (`__init__`, `start`, `stop`) is unchanged — only the implementation changes. The orchestrator, tests, and any callers continue to work without modification.

Default wake word model ships as `hey_jarvis_v0.1` (included in the `openwakeword` package) until a custom "hey tooth trust" model is trained. The `model_name` parameter on `WakeWordDetector` allows a drop-in swap to a custom `.tflite` model with no interface change.

---

## Tradeoffs Accepted

| Dimension | Porcupine | openWakeWord |
|-----------|-----------|--------------|
| License | Commercial (free tier gated) | Apache 2.0 |
| API key required | Yes | No |
| On-device inference | Yes | Yes |
| Pre-trained model coverage | Large (dozens of keywords) | Smaller (5–6 bundled) |
| Custom wake word | Cloud console (easy) | Local pipeline (more manual) |
| CPU efficiency | Very high (C engine) | Moderate (TFLite) |
| HIPAA narrative | Requires trust in Picovoice key handling | No third-party at runtime |
| Contributor onboarding | Key provisioning required | Clone and go |

The manual custom training tradeoff is accepted: the openWakeWord training pipeline is well-documented and produces production-quality models within a few hours on a laptop. The HIPAA, licensing, and contributor-friction wins outweigh the tooling convenience gap.

---

## Consequences

- `pvporcupine` removed from `requirements.txt`; `openwakeword` added.
- `PICOVOICE_ACCESS_KEY` removed from `src/config.py`, `.env.example`, and `.env`.
- `src/voice/wake_word.py` refactored; public interface preserved.
- Future task: train a custom "hey tooth trust" openWakeWord model using the project's training pipeline and replace `_DEFAULT_MODEL` with the custom `.tflite` path.
- iOS companion app wake word (future): revisit Picovoice SDK for mobile if licensing terms improve, or use openWakeWord's ONNX export with Core ML for on-device iOS inference.
