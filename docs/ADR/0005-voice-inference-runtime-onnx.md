# ADR 0005 — Voice Inference Runtime: ONNX over TFLite

**Status:** Accepted  
**Date:** 2026-05-23  
**Context:** Stage 9 voice demo, openwakeword wake word detection

---

## Context

openWakeWord supports two inference backends for loading `.tflite` and `.onnx` wake word models:

- **tflite-runtime** — Google's TFLite inference library
- **onnxruntime** — Microsoft's cross-platform ONNX inference library

When `inference_framework` is not specified (or set to `"tflite"`), openWakeWord tries to import
`tflite_runtime` first. On macOS — particularly Apple Silicon — this fails with a
`ModuleNotFoundError`, triggering a warning and a second attempt with `onnxruntime`.

During the first live run of the Stage 9 voice demo, the following error chain occurred:

```
WARNING:root:Tried to import the tflite runtime, but it was not found.
Trying to switch to onnxruntime instead, if appropriate models are available.
ModuleNotFoundError: No module named 'tflite_runtime'
ValueError: Tried to import the tflite runtime for provided tflite models,
but it was not found. Please install it using `pip install tflite-runtime`
```

The fallback to onnxruntime silently failed because `inference_framework` was still pointing
at the tflite path when the bundled `.tflite` model files were resolved.

---

## Decision

Set `inference_framework="onnx"` explicitly when constructing the openWakeWord `Model` in
`scripts/voice_demo.py`, and pin `onnxruntime>=1.19,<2` in `requirements.txt`.

---

## Rationale

| Factor | tflite-runtime | onnxruntime |
|---|---|---|
| macOS (Intel) | Inconsistent | Stable |
| macOS (Apple Silicon / ARM) | Broken / unsupported builds | Stable |
| Linux x86-64 | Stable | Stable |
| Windows | Limited | Stable |
| Package size | ~15 MB | ~30 MB |
| CI reliability | Low | High |

`tflite-runtime` has no official ARM macOS wheel on PyPI. Users on Apple Silicon must build
from source or use an unofficial wheel — a non-starter for a demo CLI that needs to work
on first `pip install`. `onnxruntime` ships pre-built wheels for all major platforms including
`macosx_arm64`, making it the reliable default.

The openwakeword bundled models ship in both `.tflite` and `.onnx` formats, so switching
inference backends requires no model re-download.

---

## Tradeoffs

- **Larger install footprint:** `onnxruntime` is ~30 MB vs `tflite-runtime` ~15 MB. Acceptable
  for a clinical workstation tool; not relevant for a demo CLI.
- **No tflite path tested:** If a future custom wake word model is trained and exported only as
  `.tflite`, the onnxruntime path will not load it. The training pipeline should export `.onnx`
  alongside `.tflite` (openwakeword's training tooling supports both).

---

## Consequences

- `scripts/voice_demo.py` passes `inference_framework="onnx"` to `Model()`.
- `requirements.txt` pins `onnxruntime>=1.19,<2`.
- `tflite-runtime` is explicitly excluded from the project's install instructions to avoid
  confusion on macOS.
- The Stage 9 voice demo runs without errors or warnings on macOS (Intel and Apple Silicon),
  Linux, and Windows.
