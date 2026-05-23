"""Stage 9 — ToothTrust voice demo CLI.

End-to-end voice pipeline:
    microphone → openWakeWord (wake detection)
              → sounddevice (5s capture)
              → Deepgram Nova-2 Medical (speech-to-text)
              → Orchestrator.route_intent (agent dispatch)
              → ElevenLabs TTS (text-to-speech)
              → sounddevice (audio playback)

Wake word:
    v1 uses "alexa" — a bundled openWakeWord model — as a stand-in for
    "Hey ToothTrust". Training a custom wake word model is a v2 task
    (see docs/IDEAS.md).

    Model download (automatic, one-time):
    openwakeword does NOT include model files in its pip package.
    On first run, _build_demo() calls openwakeword.utils.download_models()
    which fetches ~7 MB of ONNX model files from GitHub releases and caches
    them inside the package's resources/models/ directory. Subsequent runs
    skip the download if the files already exist.

Required env vars (.env):
    ANTHROPIC_API_KEY   — Claude routing and agent inference
    DEEPGRAM_API_KEY    — speech-to-text (Nova-2 Medical)
    ELEVENLABS_API_KEY  — text-to-speech
    TTS_VOICE_ID        — ElevenLabs voice ID (optional; defaults to Rachel)

Usage:
    python -m scripts.voice_demo

    Press Ctrl+C to exit.

macOS note:
    On first run macOS will prompt for microphone access.
    Approve it in System Preferences → Privacy & Security → Microphone.
"""

from __future__ import annotations

import io
import queue
import sys
import wave

import numpy as np
import sounddevice as sd

# ── Env validation (fail fast before any heavy imports) ───────────────────────

from dotenv import load_dotenv

load_dotenv()

from src.config import DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, ANTHROPIC_API_KEY  # noqa: E402

_MISSING: list[str] = []
if not ANTHROPIC_API_KEY:
    _MISSING.append("ANTHROPIC_API_KEY")
if not DEEPGRAM_API_KEY:
    _MISSING.append("DEEPGRAM_API_KEY")
if not ELEVENLABS_API_KEY:
    _MISSING.append("ELEVENLABS_API_KEY")

if _MISSING:
    print(
        f"\n[ToothTrust] ERROR — missing required env vars: {', '.join(_MISSING)}\n"
        "Copy .env.example to .env and fill in the missing keys, then re-run.\n",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Voice config ──────────────────────────────────────────────────────────────

from src.config import TTS_VOICE_ID  # noqa: E402

_SAMPLE_RATE = 16_000
_CHUNK_SIZE = 1_280          # 80 ms at 16 kHz — optimal for openWakeWord
_CAPTURE_SECONDS = 5
_WAKE_THRESHOLD = 0.5
_WAKE_MODEL_NAME = "alexa"   # bundled model; "Hey ToothTrust" is a v2 task
_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"   # ElevenLabs "Rachel" built-in
_TTS_MODEL = "eleven_turbo_v2_5"
_VOICE_RESPONSE_MAX_CHARS = 200

ANSI_GREEN  = "\033[92m"
ANSI_CYAN   = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_RESET  = "\033[0m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pcm_to_wav(audio: np.ndarray, sample_rate: int = _SAMPLE_RATE) -> bytes:
    """Wrap a mono int16 ndarray in a WAV container (in-memory)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def _truncate_for_voice(text: str, max_chars: int = _VOICE_RESPONSE_MAX_CHARS) -> str:
    """Trim a long agent response to the first sentence within max_chars."""
    if len(text) <= max_chars:
        return text
    # Try to cut on a sentence boundary within the limit
    truncated = text[:max_chars]
    for sep in (". ", "! ", "? ", "\n"):
        idx = truncated.rfind(sep)
        if idx > max_chars // 2:
            return truncated[: idx + 1].strip()
    return truncated.rstrip() + "…"


def _beep(frequency: int = 880, duration: float = 0.15) -> None:
    """Play a short confirmation tone via sounddevice."""
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    tone = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.4).astype(np.int16)
    sd.play(tone, samplerate=_SAMPLE_RATE)
    sd.wait()


# ── VoiceDemo class ───────────────────────────────────────────────────────────

class VoiceDemo:
    """Wires microphone → wake word → STT → agent → TTS into a single demo loop.

    All external clients are injected so the class is fully testable without
    live API calls.
    """

    def __init__(
        self,
        dg_client,
        el_client,
        oww_model,
        orchestrator,
        voice_id: str,
        wake_word: str = _WAKE_MODEL_NAME,
        wake_threshold: float = _WAKE_THRESHOLD,
        capture_seconds: float = _CAPTURE_SECONDS,
        sample_rate: int = _SAMPLE_RATE,
        chunk_size: int = _CHUNK_SIZE,
    ) -> None:
        self._dg = dg_client
        self._el = el_client
        self._oww = oww_model
        self._orch = orchestrator
        self._voice_id = voice_id
        self._wake_word = wake_word
        self._wake_threshold = wake_threshold
        self._capture_seconds = capture_seconds
        self._sample_rate = sample_rate
        self._chunk_size = chunk_size
        self._n_capture_chunks = int(capture_seconds * sample_rate / chunk_size)

    # ── STT ───────────────────────────────────────────────────────────────────

    def transcribe(self, audio: np.ndarray) -> str:
        """Send a mono int16 audio array to Deepgram and return the transcript."""
        wav_bytes = _pcm_to_wav(audio, self._sample_rate)
        response = self._dg.listen.v1.media.transcribe_file(
            request=wav_bytes,
            model="nova-2-medical",
            language="en-US",
            punctuate=True,
            smart_format=True,
        )
        try:
            transcript = response.results.channels[0].alternatives[0].transcript
            return (transcript or "").strip()
        except (AttributeError, IndexError):
            return ""

    # ── Agent routing ─────────────────────────────────────────────────────────

    def handle_command(self, transcript: str) -> str:
        """Route transcript through the Orchestrator and return a voice string."""
        if not transcript:
            return "Sorry, I didn't catch that. Try again."
        return self._orch.route_intent(transcript)

    # ── TTS ───────────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Convert text to speech via ElevenLabs and play via sounddevice.

        Falls back to printing the response if TTS fails.
        """
        voice_text = _truncate_for_voice(text)
        try:
            audio_iter = self._el.text_to_speech.convert(
                voice_id=self._voice_id,
                text=voice_text,
                model_id=_TTS_MODEL,
                output_format="pcm_16000",
            )
            pcm = b"".join(audio_iter)
            arr = np.frombuffer(pcm, dtype=np.int16)
            sd.play(arr, samplerate=self._sample_rate)
            sd.wait()
        except Exception as exc:
            print(
                f"{ANSI_YELLOW}[TTS fallback — ElevenLabs error: {exc}]{ANSI_RESET}\n"
                f"Response: {voice_text}"
            )

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Block forever: listen for wake word, then capture → STT → agent → TTS."""
        audio_queue: queue.Queue[np.ndarray] = queue.Queue()

        def _callback(indata: np.ndarray, frames: int, time_info, status) -> None:
            if status:
                print(f"{ANSI_YELLOW}[audio] {status}{ANSI_RESET}", file=sys.stderr)
            audio_queue.put(indata[:, 0].copy())  # keep mono channel

        print(
            f"\n{ANSI_GREEN}ToothTrust voice demo ready.{ANSI_RESET}\n"
            f"Say {ANSI_CYAN}'{self._wake_word}'{ANSI_RESET} "
            "(placeholder wake word) followed by a command.\n"
            "Press Ctrl+C to exit.\n"
        )

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._chunk_size,
                callback=_callback,
            ):
                while True:
                    chunk = audio_queue.get()
                    scores = self._oww.predict(chunk)
                    if scores.get(self._wake_word, 0.0) >= self._wake_threshold:
                        print(f"\n{ANSI_CYAN}[wake word detected]{ANSI_RESET} Listening…")
                        _beep()

                        # Drain stale chunks before capture
                        while not audio_queue.empty():
                            audio_queue.get_nowait()

                        capture: list[np.ndarray] = []
                        for _ in range(self._n_capture_chunks):
                            capture.append(audio_queue.get())
                        audio_data = np.concatenate(capture)

                        transcript = self.transcribe(audio_data)
                        print(f"[transcript] {transcript!r}")

                        response_text = self.handle_command(transcript)
                        full_log = response_text
                        print(f"[response]   {full_log[:200]}{'…' if len(full_log) > 200 else ''}")

                        self.speak(response_text)

        except sd.PortAudioError as exc:
            print(
                f"\n[ToothTrust] ERROR — microphone access failed: {exc}\n"
                "On macOS, approve microphone access in "
                "System Preferences → Privacy & Security → Microphone.\n",
                file=sys.stderr,
            )
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n[ToothTrust] Goodbye.")


# ── Factory ───────────────────────────────────────────────────────────────────

def _build_demo() -> VoiceDemo:
    """Initialise all clients and return a ready VoiceDemo instance."""
    from deepgram import DeepgramClient
    from elevenlabs.client import ElevenLabs
    from openwakeword.model import Model

    from src.orchestrator import Orchestrator

    # Download wake word + feature models on first run (no-op if already present).
    # openwakeword does NOT bundle model files in its pip package — they are fetched
    # from GitHub releases the first time and cached inside the package's resources dir.
    from openwakeword.utils import download_models
    print("Checking openWakeWord models (downloads on first run)…")
    download_models([_WAKE_MODEL_NAME])

    dg_client = DeepgramClient(api_key=DEEPGRAM_API_KEY)
    el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    oww_model = Model(wakeword_models=[_WAKE_MODEL_NAME], inference_framework="onnx")
    orchestrator = Orchestrator()

    voice_id = TTS_VOICE_ID or _DEFAULT_VOICE_ID

    return VoiceDemo(
        dg_client=dg_client,
        el_client=el_client,
        oww_model=oww_model,
        orchestrator=orchestrator,
        voice_id=voice_id,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    demo = _build_demo()
    demo.run()


if __name__ == "__main__":
    main()
