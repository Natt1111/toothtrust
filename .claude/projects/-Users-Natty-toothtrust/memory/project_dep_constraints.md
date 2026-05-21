---
name: project-dep-constraints
description: Resolved dependency constraints for ToothTrust on Python 3.11 / macOS — needed to get tests passing
metadata:
  type: project
---

PyTorch 2.4+ wheels are not available for Python 3.11 on this macOS system via the default pip index; max available is `torch==2.2.2`.

`sentence-transformers>=5.0` requires PyTorch ≥ 2.4 → pinned to `sentence-transformers<5.0` (resolves to 4.1.0).

`transformers>=4.57` requires `torch.compiler` (PyTorch ≥ 2.1) → resolved by upgrading torch to 2.2.2.

**Why:** Initial `pip install -r requirements.txt` picked up sentence-transformers 5.5.1 which blew up at import time with `NameError: nn` / `AttributeError: torch.compiler`. Two-step fix: pin sentence-transformers to 4.x, upgrade torch to 2.2.2.

**How to apply:** If requirements.txt is ever regenerated or another dev sets up the project on a similar macOS system, add `torch==2.2.2` and `sentence-transformers<5.0` as explicit pins until PyTorch ≥ 2.4 wheels become available for this platform.
