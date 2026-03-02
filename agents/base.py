"""Base agent with shared Gemini client and utilities."""

from abc import ABC, abstractmethod
from typing import Any

from google import genai
from google.genai import types
from loguru import logger

from core.config import get_settings
from models.schemas import AgentState


class BaseAgent(ABC):
    """Base class for all agents using Gemini with function calling."""

    def __init__(self) -> None:
        self._client: genai.Client | None = None
        self._settings = get_settings()

    @property
    def client(self) -> genai.Client:
        """Lazy-initialize Gemini client."""
        if self._client is None:
            if not self._settings.gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY is required. Set it in .env or environment."
                )
            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    @property
    def model(self) -> str:
        return self._settings.gemini_model

    def _count_tokens(self, text: str) -> int:
        """Approximate token count (4 chars ~ 1 token for English)."""
        return max(1, len(text) // 4)

    def _update_token_usage(self, state: AgentState, prompt: str, response: str) -> None:
        """Track token usage in agent state."""
        prompt_tokens = self._count_tokens(prompt)
        completion_tokens = self._count_tokens(response)
        state.token_usage["prompt_tokens"] = state.token_usage.get("prompt_tokens", 0) + prompt_tokens
        state.token_usage["completion_tokens"] = state.token_usage.get("completion_tokens", 0) + completion_tokens

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """Execute agent logic. Mutates and returns state."""
        ...
