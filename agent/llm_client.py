"""DeepSeek LLM client for the agent runtime.

Communicates with the DeepSeek API using the OpenAI-compatible chat completions
endpoint. This module handles ONLY LLM communication — no database, no secrets
from the backend, no cloud SDK access. Fully contract-compliant.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single message in the conversation history."""
    role: str  # "system", "user", "assistant"
    content: str


class DeepSeekClient:
    """Minimal client for DeepSeek's OpenAI-compatible API.

    Uses only the Python standard library (urllib) to avoid adding
    heavy dependencies like httpx/requests to the agent package,
    which would violate the architectural boundary tests.
    """

    def __init__(self, api_key: str, config: Optional[AgentConfig] = None) -> None:
        self._api_key = api_key
        self._config = config or AgentConfig()
        self._base_url = self._config.api_base_url.rstrip("/")

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat completion request to DeepSeek and return the response text.

        Uses asyncio.to_thread to avoid blocking the event loop with urllib.
        """
        import asyncio
        return await asyncio.to_thread(
            self._sync_chat_completion,
            messages,
            temperature,
            max_tokens,
        )

    def _sync_chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Synchronous implementation using only stdlib urllib."""
        import urllib.request
        import urllib.error

        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._config.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self._config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._config.max_tokens,
            "stream": False,
        }

        request_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                return response_data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.error(
                "DeepSeek API error: status=%d body=%s", e.code, error_body
            )
            raise RuntimeError(
                f"DeepSeek API returned HTTP {e.code}: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            logger.error("DeepSeek API connection error: %s", e.reason)
            raise RuntimeError(
                f"Failed to connect to DeepSeek API: {e.reason}"
            ) from e
