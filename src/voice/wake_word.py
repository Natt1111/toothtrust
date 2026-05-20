"""Wake word detection using openWakeWord (free, open-source, no API key required)."""

from __future__ import annotations

import threading
from typing import Callable

try:
    import numpy as np
    import sounddevice as sd
    from openwakeword.model import Model as OWWModel
    _OWW_AVAILABLE = True
except ImportError:
    _OWW_AVAILABLE = False

# openWakeWord ships several pre-trained models; default to the included "hey jarvis"
# wake word as a functional stand-in. Swap WAKE_WORD_MODEL for a custom .tflite model
# trained via the openWakeWord training pipeline when a "hey tooth trust" model exists.
_DEFAULT_MODEL = "hey_jarvis_v0.1"
_SAMPLE_RATE = 16_000
_CHUNK_FRAMES = 1_280  # 80 ms at 16 kHz — recommended by openWakeWord


class WakeWordDetector:
    """Listen for the wake word in a background thread; fire a callback when detected."""

    def __init__(
        self,
        on_wake: Callable[[], None],
        model_name: str = _DEFAULT_MODEL,
        threshold: float = 0.5,
    ) -> None:
        if not _OWW_AVAILABLE:
            raise RuntimeError(
                "openwakeword and sounddevice must be installed for wake word detection. "
                "Run: pip install openwakeword sounddevice"
            )
        self._on_wake = on_wake
        self._model_name = model_name
        self._threshold = threshold
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        model = OWWModel(wakeword_models=[self._model_name], inference_framework="tflite")

        with sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=_CHUNK_FRAMES,
        ) as stream:
            while self._running:
                pcm, _ = stream.read(_CHUNK_FRAMES)
                # openWakeWord expects a flat float32 or int16 numpy array
                audio_chunk = pcm.flatten()
                prediction = model.predict(audio_chunk)
                score = prediction.get(self._model_name, 0.0)
                if score >= self._threshold:
                    self._on_wake()
