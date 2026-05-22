"""Base agent: shared Claude client, abstract run() interface, JSON helpers, and anti-hallucination validators."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# CDT codes follow the pattern D + exactly 4 digits (e.g. D2750, D0150).
_CDT_FORMAT = re.compile(r"^D\d{4}$")

# Phrases that signal the model is speaking as an AI rather than grounding in evidence.
_PREAMBLE_PATTERNS = re.compile(
    r"^(as an ai|i (am|'m) an ai|i cannot provide (medical|clinical)|"
    r"i (don't|do not) have access to)",
    re.IGNORECASE,
)


class BaseAgent(ABC):
    system_prompt: str = ""
    max_tokens: int = 1024

    def _call(self, user_message: str, system: str | None = None) -> str:
        response = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=self.max_tokens,
            system=system or self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    # ── JSON parsing ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Strip markdown code fences and parse JSON.

        Claude occasionally wraps JSON responses in ```json ... ``` blocks despite
        instructions to return plain JSON. Tries stripped string first, then raw.
        Raises ValueError with a clear message if both attempts fail.
        """
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError(
                f"Response is not valid JSON after fence stripping. "
                f"First 200 chars: {raw[:200]!r}"
            )

    # ── Anti-hallucination validators ─────────────────────────────────────────

    @staticmethod
    def _validate_cdt_format(code: str) -> bool:
        """Return True if code matches the CDT format D + 4 digits (e.g. D2750)."""
        return bool(_CDT_FORMAT.match(code.strip()))

    @staticmethod
    def _validate_citations(citations: list[str], allowed_sources: set[str]) -> list[str]:
        """Return list of citations that are NOT in the allowed source set.

        A non-empty return value means the model cited sources it was not given —
        a hallucination signal that should be surfaced as a validation warning.
        """
        return [c for c in citations if c not in allowed_sources]

    @staticmethod
    def _has_ai_preamble(text: str) -> bool:
        """Return True if the response begins with an AI-speaker preamble.

        These phrases indicate the model is narrating its own limitations rather
        than grounding its response in the provided evidence.
        """
        return bool(_PREAMBLE_PATTERNS.match(text.strip()))

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Execute the agent's task. Returns a result dict."""
