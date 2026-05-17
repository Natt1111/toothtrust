"""Wake word detection using Picovoice Porcupine."""

from __future__ import annotations

import threading
from typing import Callable

try:
    import pvporcupine
    import sounddevice as sd
    import numpy as np
    _PORCUPINE_AVAILABLE = True
except ImportError:
    _PORCUPINE_AVAILABLE = False

from src.config import PICOVOICE_ACCESS_KEY


class WakeWordDetector:
    """Listen for the wake word in a background thread; fire a callback when detected."""

    def __init__(self, on_wake: Callable[[], None], keywords: list[str] | None = None) -> None:
        if not _PORCUPINE_AVAILABLE:
            raise RuntimeError("pvporcupine and sounddevice must be installed for wake word detection.")
        self._on_wake = on_wake
        self._keywords = keywords or ["porcupine"]
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
        porcupine = pvporcupine.create(
            access_key=PICOVOICE_ACCESS_KEY,
            keywords=self._keywords,
        )
        frame_length = porcupine.frame_length
        sample_rate = porcupine.sample_rate

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frame_length,
        ) as stream:
            while self._running:
                pcm, _ = stream.read(frame_length)
                pcm_flat = pcm.flatten().tolist()
                keyword_index = porcupine.process(pcm_flat)
                if keyword_index >= 0:
                    self._on_wake()

        porcupine.delete()
