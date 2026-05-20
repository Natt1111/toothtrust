"""Base agent: shared Claude client, abstract run() interface, and JSON response helpers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

import anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


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

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Strip markdown code fences and parse JSON.

        Claude occasionally wraps JSON responses in ```json ... ``` blocks despite
        instructions to return plain JSON. This strips those fences before parsing.

        Tries the stripped string first, then falls back to the raw string.
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

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Execute the agent's task. Returns a result dict."""
