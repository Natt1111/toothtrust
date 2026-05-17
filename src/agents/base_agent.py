"""Base agent: shared Claude client and abstract run() interface."""

from __future__ import annotations

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

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Execute the agent's task. Returns a result dict."""
