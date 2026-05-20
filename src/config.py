"""Central configuration — all settings loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# --- API keys ---
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")

# --- Model settings ---
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Vector DB ---
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_db"))
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "dental_evidence")
# Raised from 5→7: Stage 7 testing showed top_k=5 missed caries_classification_icdas.md for Case 1
TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "7"))

# --- Data paths ---
CORPUS_DIR: Path = BASE_DIR / "data" / "corpus"
MOCK_CASES_DIR: Path = BASE_DIR / "data" / "mock_cases"
CDT_CODES_PATH: Path = BASE_DIR / "data" / "cdt_codes.json"

# --- Voice ---
WAKE_WORD: str = os.getenv("WAKE_WORD", "hey tooth trust")
STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "en-US")
TTS_VOICE_ID: str = os.getenv("TTS_VOICE_ID", "")

# --- API server ---
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
