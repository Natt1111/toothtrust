"""Speech-to-text via Deepgram Nova-2."""

from __future__ import annotations

import io

from src.config import DEEPGRAM_API_KEY, STT_LANGUAGE

try:
    from deepgram import DeepgramClient, PrerecordedOptions
    _DEEPGRAM_AVAILABLE = True
except ImportError:
    _DEEPGRAM_AVAILABLE = False


class SpeechToText:
    def __init__(self) -> None:
        if not _DEEPGRAM_AVAILABLE:
            raise RuntimeError("deepgram-sdk must be installed.")
        self._client = DeepgramClient(DEEPGRAM_API_KEY)

    def transcribe_bytes(self, audio_bytes: bytes, mimetype: str = "audio/wav") -> str:
        """Transcribe raw audio bytes. Returns transcript string."""
        options = PrerecordedOptions(
            model="nova-2-medical",
            language=STT_LANGUAGE,
            smart_format=True,
            punctuate=True,
        )
        source = {"buffer": io.BytesIO(audio_bytes), "mimetype": mimetype}
        response = self._client.listen.prerecorded.v("1").transcribe_file(source, options)
        try:
            return response["results"]["channels"][0]["alternatives"][0]["transcript"]
        except (KeyError, IndexError):
            return ""

    def transcribe_file(self, path: str) -> str:
        """Transcribe an audio file by path. Returns transcript string."""
        with open(path, "rb") as f:
            return self.transcribe_bytes(f.read())
