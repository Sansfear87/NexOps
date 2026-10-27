"""Multi-model LLM client for DeepSeek and NVIDIA Nemotron on Nebius AI Cloud.

Communicates with OpenAI-compatible chat completion endpoints for:
1. DeepSeek (high-throughput, cost-efficient fast coder).
2. NVIDIA Nemotron-4-340B via Nebius AI Cloud (high-complexity causal reasoning).

Architectural Invariant:
Strictly uses the Python standard library (urllib.request) inside asyncio.to_thread.
Zero external HTTP dependencies (no httpx, no requests, no aiohttp).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import AgentConfig
from .credit_optimizer import (
    ModelPricing,
    ResponseCache,
    TokenBudgetManager,
    get_model_pricing,
)

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single message in the conversation history."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Structured response from LLM inference including usage and cost telemetry."""
    content: str
    model_name: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0
    cached: bool = False


class MultiModelLLMClient:
    """Unified client for DeepSeek and NVIDIA Nemotron (Nebius) models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        nebius_api_key: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        budget_manager: Optional[TokenBudgetManager] = None,
        cache: Optional[ResponseCache] = None,
    ) -> None:
        self._config = config or AgentConfig()
        self._api_key = api_key or ""
        self._nebius_api_key = nebius_api_key or self._config.nebius_api_key or self._api_key
        self.budget_manager = budget_manager
        self.cache = cache if (cache is not None) else (
            ResponseCache(max_entries=self._config.cache_max_entries)
            if self._config.enable_response_cache else None
        )
        self.default_model = self._config.model_name

    async def complete(
        self,
        messages: List[ChatMessage],
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        role: Optional[str] = None,
    ) -> LLMResponse:
        """Asynchronously send chat completion request using stdlib urllib in thread pool."""
        return await asyncio.to_thread(
            self._sync_chat_completion,
            messages=messages,
            model_name=model_name,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            role=role,
        )

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Backward-compatible helper returning raw string output."""
        res = await self.complete(
            messages=messages,
            model_name=model_name or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return res.content

    def _sync_chat_completion(
        self,
        messages: List[ChatMessage],
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        role: Optional[str] = None,
    ) -> LLMResponse:
        """Synchronously execute chat completion with token and cost tracking."""
        start_ts = time.perf_counter()

        target_model = model_name or self.default_model
        is_nemotron = ("nemotron" in target_model.lower()) or (provider == "nebius")

        if is_nemotron:
            base_url = self._config.nebius_api_base.rstrip("/")
            auth_token = self._nebius_api_key
            effective_provider = "nebius"
        else:
            base_url = self._config.api_base_url.rstrip("/")
            auth_token = self._api_key
            effective_provider = "deepseek"

        url = f"{base_url}/chat/completions"

        # Check in-memory cache for deterministic reuse
        cache_key = None
        if self.cache is not None:
            cache_payload = {
                "model": target_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temp": temperature if temperature is not None else self._config.temperature,
            }
            cache_key = ResponseCache.hash_key("llm_completion", cache_payload)
            cached_item = self.cache.get(cache_key)
            if cached_item is not None:
                logger.info("ResponseCache HIT for model=%s key=%s", target_model, cache_key[:12])
                return LLMResponse(
                    content=cached_item["content"],
                    model_name=target_model,
                    provider=effective_provider,
                    prompt_tokens=cached_item.get("prompt_tokens", 0),
                    completion_tokens=cached_item.get("completion_tokens", 0),
                    total_tokens=cached_item.get("total_tokens", 0),
                    estimated_cost_usd=0.0,
                    latency_ms=int((time.perf_counter() - start_ts) * 1000),
                    cached=True,
                )

        payload = {
            "model": target_model,
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
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_text = resp.read().decode("utf-8")
                response_data = json.loads(resp_text)

            content = response_data["choices"][0]["message"]["content"]
            usage = response_data.get("usage", {})

            # Calculate token counts
            prompt_tokens = usage.get("prompt_tokens")
            if prompt_tokens is None:
                prompt_tokens = sum(len(m.content) for m in messages) // 4

            completion_tokens = usage.get("completion_tokens")
            if completion_tokens is None:
                completion_tokens = len(content) // 4

            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            # Pricing & accounting
            pricing = get_model_pricing(target_model)
            cost_usd = pricing.calculate_cost(prompt_tokens, completion_tokens)

            if self.budget_manager is not None:
                self.budget_manager.record_usage(
                    model_name=target_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    role=role,
                )

            latency_ms = int((time.perf_counter() - start_ts) * 1000)

            # Store in cache
            if self.cache is not None and cache_key is not None:
                self.cache.set(
                    key=cache_key,
                    value={
                        "content": content,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    },
                    tokens_estimate=total_tokens,
                    cost_estimate_usd=cost_usd,
                )

            return LLMResponse(
                content=content,
                model_name=target_model,
                provider=effective_provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost_usd,
                latency_ms=latency_ms,
                cached=False,
            )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.error(
                "API error from %s (%s): status=%d body=%s",
                effective_provider, target_model, e.code, error_body
            )
            raise RuntimeError(
                f"{effective_provider.upper()} API returned HTTP {e.code}: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            logger.error("Connection error to %s: %s", url, e.reason)
            raise RuntimeError(
                f"Failed to connect to {effective_provider.upper()} API ({url}): {e.reason}"
            ) from e


class DeepSeekClient(MultiModelLLMClient):
    """Specialized client for DeepSeek endpoints, maintaining backward compatibility."""

    def __init__(self, api_key: str, config: Optional[AgentConfig] = None) -> None:
        cfg = config or AgentConfig()
        super().__init__(api_key=api_key, config=cfg)
        self.default_model = cfg.model_name


class NemotronClient(MultiModelLLMClient):
    """Specialized client for NVIDIA Nemotron-4-340B on Nebius AI Cloud."""

    def __init__(self, api_key: Optional[str] = None, config: Optional[AgentConfig] = None) -> None:
        cfg = config or AgentConfig()
        effective_key = api_key or cfg.nebius_api_key or ""
        super().__init__(
            api_key=effective_key,
            nebius_api_key=effective_key,
            config=cfg,
        )
        self.default_model = cfg.nemotron_model_name
