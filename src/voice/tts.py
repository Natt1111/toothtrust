"""Text-to-speech via ElevenLabs."""

from __future__ import annotations

from src.config import ELEVENLABS_API_KEY, TTS_VOICE_ID

try:
    from elevenlabs import ElevenLabs, play
    _ELEVENLABS_AVAILABLE = True
except ImportError:
    _ELEVENLABS_AVAILABLE = False

# "Rachel" — a stock ElevenLabs voice. The API requires the voice's ID, not its name.
_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


class TextToSpeech:
    def __init__(self, voice_id: str = "") -> None:
        if not _ELEVENLABS_AVAILABLE:
            raise RuntimeError("elevenlabs must be installed.")
        self._client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        self._voice_id = voice_id or TTS_VOICE_ID or _DEFAULT_VOICE_ID

    def speak(self, text: str) -> None:
        """Synthesize text and play it through the default audio output."""
        audio = self._client.text_to_speech.convert(
            voice_id=self._voice_id,
            text=text,
            model_id="eleven_turbo_v2",
            output_format="mp3_44100_128",
        )
        play(audio)

    def synthesize(self, text: str) -> bytes:
        """Synthesize text and return raw audio bytes (MP3)."""
        audio_iter = self._client.text_to_speech.convert(
            voice_id=self._voice_id,
            text=text,
            model_id="eleven_turbo_v2",
            output_format="mp3_44100_128",
        )
        return b"".join(audio_iter)
