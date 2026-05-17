"""Text-to-speech via ElevenLabs."""

from __future__ import annotations

from src.config import ELEVENLABS_API_KEY, TTS_VOICE_ID

try:
    from elevenlabs import ElevenLabs, play
    _ELEVENLABS_AVAILABLE = True
except ImportError:
    _ELEVENLABS_AVAILABLE = False


class TextToSpeech:
    def __init__(self, voice_id: str = "") -> None:
        if not _ELEVENLABS_AVAILABLE:
            raise RuntimeError("elevenlabs must be installed.")
        self._client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        self._voice_id = voice_id or TTS_VOICE_ID or "Rachel"

    def speak(self, text: str) -> None:
        """Synthesize text and play it through the default audio output."""
        audio = self._client.generate(
            text=text,
            voice=self._voice_id,
            model="eleven_turbo_v2",
        )
        play(audio)

    def synthesize(self, text: str) -> bytes:
        """Synthesize text and return raw audio bytes (MP3)."""
        audio_iter = self._client.generate(
            text=text,
            voice=self._voice_id,
            model="eleven_turbo_v2",
            stream=False,
        )
        return b"".join(audio_iter)
