"""Credit and token efficiency optimizer for the Agent Subsystem.

Provides enterprise-grade credit optimization:
1. Multi-model pricing tables & cost accounting (DeepSeek vs NVIDIA Nemotron on Nebius Token Factory).
2. TokenBudgetManager with strict budget limits, role-based tracking, and kill switches.
3. PromptPruner for sliding-window context compression & large observation truncation.
4. ResponseCache & ObservationCache for deduplicating identical calls.
5. SemanticComplexityRouter for optimal routing across Nebius Token Factory endpoints:
   - nvidia/Nemotron-3_5-Lightning (rapid reasoning & coordination)
   - nvidia/Nemotron-3.5-Super-VL (multimodal, deep logs & incident root causes)
   - deepseek-ai/DeepSeek-V4.1-Flash-1017 (fast diffs, syntax & test checks)
   - deepseek-ai/DeepSeek-V4-Pro-0813 (comprehensive PR code review & architecture)

Conforms to architectural boundaries: strictly uses standard library modules.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Model Pricing & Cost Accounting
# ---------------------------------------------------------------------------

@dataclass
class ModelPricing:
    """Pricing configuration in USD per 1 Million tokens."""
    input_cost_per_million: float
    output_cost_per_million: float

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD."""
        cost = (
            (prompt_tokens / 1_000_000.0) * self.input_cost_per_million
            + (completion_tokens / 1_000_000.0) * self.output_cost_per_million
        )
        return round(cost, 6)


# Canonical pricing registry per model
MODEL_PRICING_REGISTRY: Dict[str, ModelPricing] = {
    # Nebius AI Cloud Token Factory Models:
    "nvidia/Nemotron-3_5-Lightning": ModelPricing(input_cost_per_million=0.30, output_cost_per_million=0.60),
    "nvidia/Nemotron-3.5-Super-VL": ModelPricing(input_cost_per_million=0.75, output_cost_per_million=2.25),
    "deepseek-ai/DeepSeek-V4.1-Flash-1017": ModelPricing(input_cost_per_million=0.10, output_cost_per_million=0.20),
    "deepseek-ai/DeepSeek-V4-Pro-0813": ModelPricing(input_cost_per_million=0.45, output_cost_per_million=1.35),

    # Legacy & Direct API references:
    "deepseek-chat": ModelPricing(input_cost_per_million=0.14, output_cost_per_million=0.28),
    "deepseek-coder": ModelPricing(input_cost_per_million=0.14, output_cost_per_million=0.28),
    "deepseek-ai/DeepSeek-V3": ModelPricing(input_cost_per_million=0.14, output_cost_per_million=0.28),
    "nvidia/nemotron-4-340b-instruct": ModelPricing(input_cost_per_million=1.00, output_cost_per_million=3.00),
    "nemotron-70b": ModelPricing(input_cost_per_million=0.50, output_cost_per_million=1.50),

    # Default fallback rate
    "default": ModelPricing(input_cost_per_million=0.20, output_cost_per_million=0.50),
}


def get_model_pricing(model_name: str) -> ModelPricing:
    """Retrieve pricing for a given model or closest match."""
    if model_name in MODEL_PRICING_REGISTRY:
        return MODEL_PRICING_REGISTRY[model_name]
    
    # Prefix / substring match
    model_lower = model_name.lower()
    if "super-vl" in model_lower or "super_vl" in model_lower:
        return MODEL_PRICING_REGISTRY["nvidia/Nemotron-3.5-Super-VL"]
    elif "lightning" in model_lower:
        return MODEL_PRICING_REGISTRY["nvidia/Nemotron-3_5-Lightning"]
    elif "flash" in model_lower or "1017" in model_lower:
        return MODEL_PRICING_REGISTRY["deepseek-ai/DeepSeek-V4.1-Flash-1017"]
    elif "pro" in model_lower or "0813" in model_lower:
        return MODEL_PRICING_REGISTRY["deepseek-ai/DeepSeek-V4-Pro-0813"]
    elif "nemotron" in model_lower:
        return MODEL_PRICING_REGISTRY["nvidia/nemotron-4-340b-instruct"]
    elif "deepseek" in model_lower:
        return MODEL_PRICING_REGISTRY["deepseek-chat"]
    
    return MODEL_PRICING_REGISTRY["default"]


# ---------------------------------------------------------------------------
# 2. Semantic Complexity Routing
# ---------------------------------------------------------------------------

class ComplexityTier(str, Enum):
    FAST = "FAST"              # High throughput, routine tasks (DeepSeek Flash)
    REASONING = "REASONING"    # High cognitive reasoning, architectural/incident tasks (Nemotron)


@dataclass
class ModelRoute:
    model_name: str
    provider: str
    complexity: ComplexityTier
    reason: str
    max_tokens: int = 4096


class SemanticComplexityRouter:
    """Routes DevOps subtasks across Nebius Token Factory endpoints and DeepSeek."""

    # Specific Nebius Token Factory Model Endpoints
    NEMOTRON_LIGHTNING = "nvidia/Nemotron-3_5-Lightning"
    NEMOTRON_SUPER_VL = "nvidia/Nemotron-3.5-Super-VL"
    DEEPSEEK_FLASH = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
    DEEPSEEK_PRO = "deepseek-ai/DeepSeek-V4-Pro-0813"

    # Default aliases
    DEEPSEEK_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
    NEMOTRON_MODEL = "nvidia/Nemotron-3_5-Lightning"

    HIGH_REASONING_KEYWORDS = {
        "incident", "root cause", "post-mortem", "vulnerability", "security audit",
        "cve", "memory leak", "deadlock", "architectural review", "rollback planning",
        "cascading failure", "outage", "risk assessment", "auth breach", "exploit",
    }

    FAST_KEYWORDS = {
        "diff", "lint", "syntax", "format", "test status", "unit test",
        "fetch pr", "list deployments", "ping", "metrics check", "health check",
    }

    @classmethod
    def decide_route(
        cls,
        goal: str,
        role: Optional[str] = None,
        risk_score: float = 0.0,
        content_length: int = 0,
    ) -> ModelRoute:
        """Decide the optimal model route balancing cost efficiency and reasoning depth."""
        goal_lower = goal.lower()
        role_upper = (role or "").upper()

        # 1. Critical risk threshold automatically elevates to Nemotron
        if risk_score >= 0.65:
            target = cls.NEMOTRON_SUPER_VL if any(k in goal_lower for k in ("incident", "root cause", "log", "metric", "cve")) else cls.NEMOTRON_LIGHTNING
            return ModelRoute(
                model_name=target,
                provider="nebius",
                complexity=ComplexityTier.REASONING,
                reason=f"High risk score ({risk_score:.2f} >= 0.65) requires Nemotron deep causal reasoning",
                max_tokens=4096,
            )

        # 2. Incident diagnostician and deep security reviews require Nemotron
        if role_upper in ("DIAGNOSTICIAN",) or any(kw in goal_lower for kw in cls.HIGH_REASONING_KEYWORDS):
            target = cls.NEMOTRON_SUPER_VL if any(k in goal_lower for k in ("incident", "root cause", "log", "metric")) else cls.NEMOTRON_LIGHTNING
            return ModelRoute(
                model_name=target,
                provider="nebius",
                complexity=ComplexityTier.REASONING,
                reason=f"Task involves deep reasoning / incident diagnostics: '{goal[:60]}'",
                max_tokens=4096,
            )

        # 3. Very large input contexts benefit from Nemotron's extensive window
        if content_length > 12000:
            return ModelRoute(
                model_name=cls.NEMOTRON_LIGHTNING,
                provider="nebius",
                complexity=ComplexityTier.REASONING,
                reason=f"Large content payload ({content_length} chars) routed to Nemotron Lightning for context retention",
                max_tokens=4096,
            )

        # 4. PR Code Review with deep analysis -> DeepSeek V4 Pro
        if role_upper == "REVIEWER" and ("security" in goal_lower or "review" in goal_lower or "pr" in goal_lower):
            return ModelRoute(
                model_name=cls.DEEPSEEK_PRO,
                provider="nebius",
                complexity=ComplexityTier.FAST,
                reason=f"PR code review routed to DeepSeek V4 Pro: '{goal[:60]}'",
                max_tokens=3072,
            )

        # 5. Default to economical DeepSeek Flash on Nebius Token Factory for routine execution
        return ModelRoute(
            model_name=cls.DEEPSEEK_FLASH,
            provider="nebius",
            complexity=ComplexityTier.FAST,
            reason=f"Task routed to DeepSeek V4.1 Flash for maximum throughput and credit efficiency: '{goal[:60]}'",
            max_tokens=2048,
        )


# ---------------------------------------------------------------------------
# 3. Token & Credit Budget Manager
# ---------------------------------------------------------------------------

class BudgetExceededException(Exception):
    """Raised when token or cost budget is breached."""
    pass


@dataclass
class TokenBudgetManager:
    """Tracks token consumption, calculates costs in USD, and enforces hard limits."""

    max_tokens_budget: int = 50_000
    max_cost_usd_budget: float = 0.50
    warning_threshold_pct: float = 0.80

    cumulative_prompt_tokens: int = 0
    cumulative_completion_tokens: int = 0
    cumulative_cost_usd: float = 0.0

    # Detailed accounting breakdowns
    tokens_by_model: Dict[str, Dict[str, int]] = field(default_factory=dict)
    tokens_by_role: Dict[str, Dict[str, int]] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    call_counts: Dict[str, int] = field(default_factory=dict)

    def record_usage(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        role: Optional[str] = None,
    ) -> float:
        """Record token usage for an LLM call and update cumulative costs."""
        pricing = get_model_pricing(model_name)
        call_cost = pricing.calculate_cost(prompt_tokens, completion_tokens)

        self.cumulative_prompt_tokens += prompt_tokens
        self.cumulative_completion_tokens += completion_tokens
        self.cumulative_cost_usd = round(self.cumulative_cost_usd + call_cost, 6)

        # Track by model
        if model_name not in self.tokens_by_model:
            self.tokens_by_model[model_name] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            self.cost_by_model[model_name] = 0.0
            self.call_counts[model_name] = 0

        self.tokens_by_model[model_name]["prompt_tokens"] += prompt_tokens
        self.tokens_by_model[model_name]["completion_tokens"] += completion_tokens
        self.tokens_by_model[model_name]["total_tokens"] += (prompt_tokens + completion_tokens)
        self.cost_by_model[model_name] = round(self.cost_by_model[model_name] + call_cost, 6)
        self.call_counts[model_name] += 1

        # Track by role
        role_key = (role or "GENERAL").upper()
        if role_key not in self.tokens_by_role:
            self.tokens_by_role[role_key] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.tokens_by_role[role_key]["prompt_tokens"] += prompt_tokens
        self.tokens_by_role[role_key]["completion_tokens"] += completion_tokens
        self.tokens_by_role[role_key]["total_tokens"] += (prompt_tokens + completion_tokens)

        logger.debug(
            "Recorded usage: %s (prompt=%d, completion=%d, cost=$%.6f, total_cost=$%.6f)",
            model_name, prompt_tokens, completion_tokens, call_cost, self.cumulative_cost_usd
        )
        return call_cost

    @property
    def total_tokens(self) -> int:
        return self.cumulative_prompt_tokens + self.cumulative_completion_tokens

    def is_budget_exceeded(self) -> bool:
        """Check if token limit or cost limit has been breached."""
        if self.total_tokens >= self.max_tokens_budget:
            return True
        if self.cumulative_cost_usd >= self.max_cost_usd_budget:
            return True
        return False

    def is_warning_threshold(self) -> bool:
        """Check if current spend is near the budget limit."""
        token_ratio = self.total_tokens / max(1, self.max_tokens_budget)
        cost_ratio = self.cumulative_cost_usd / max(0.0001, self.max_cost_usd_budget)
        return token_ratio >= self.warning_threshold_pct or cost_ratio >= self.warning_threshold_pct

    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens_budget - self.total_tokens)

    def remaining_budget_usd(self) -> float:
        return max(0.0, round(self.max_cost_usd_budget - self.cumulative_cost_usd, 6))

    def get_metrics(self) -> Dict[str, Any]:
        """Return comprehensive telemetry of credit and token usage."""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.cumulative_prompt_tokens,
            "completion_tokens": self.cumulative_completion_tokens,
            "total_cost_usd": self.cumulative_cost_usd,
            "remaining_budget_usd": self.remaining_budget_usd(),
            "remaining_tokens": self.remaining_tokens(),
            "budget_exceeded": self.is_budget_exceeded(),
            "tokens_by_model": self.tokens_by_model,
            "tokens_by_role": self.tokens_by_role,
            "cost_by_model": self.cost_by_model,
            "call_counts": self.call_counts,
        }


# ---------------------------------------------------------------------------
# 4. Prompt Pruning & Observation Compression
# ---------------------------------------------------------------------------

class PromptPruner:
    """Compresses prompts, trims redundant history, and truncates large tool observations."""

    def __init__(
        self,
        max_observation_chars: int = 1500,
        max_history_turns: int = 8,
    ):
        self.max_observation_chars = max_observation_chars
        self.max_history_turns = max_history_turns
        self.total_chars_pruned: int = 0
        self.total_tokens_saved_estimate: int = 0

    def prune_observation(self, content: str, max_chars: Optional[int] = None) -> Tuple[str, int]:
        """Truncate long tool output (logs, diffs, JSON) while retaining diagnostic headers and footers."""
        limit = max_chars or self.max_observation_chars
        if len(content) <= limit:
            return content, 0

        # Smart head/tail extraction with informative notice
        head_chars = int(limit * 0.6)
        tail_chars = int(limit * 0.3)
        truncated_count = len(content) - (head_chars + tail_chars)

        head = content[:head_chars]
        tail = content[-tail_chars:] if tail_chars > 0 else ""

        pruned = (
            f"{head}\n\n"
            f"[... OMITTED {truncated_count} CHARACTERS FOR CREDIT EFFICIENCY ...]\n\n"
            f"{tail}"
        )

        chars_saved = len(content) - len(pruned)
        tokens_saved = chars_saved // 4
        self.total_chars_pruned += chars_saved
        self.total_tokens_saved_estimate += tokens_saved

        return pruned, tokens_saved

    def compress_history(self, messages: List[Any], keep_recent_turns: Optional[int] = None) -> List[Any]:
        """Apply a sliding window to conversation turns while preserving system instructions.

        Retains:
        - System prompt (index 0)
        - Initial user goal (index 1)
        - The most recent N turns in full detail
        Old intermediate observations in between are pruned/compacted.
        """
        turns_to_keep = keep_recent_turns or self.max_history_turns
        if len(messages) <= (turns_to_keep + 2):
            return messages

        # Preserve head
        head_msgs = messages[:2]
        tail_msgs = messages[-turns_to_keep:]

        # Compact middle messages
        middle_msgs = messages[2:-turns_to_keep]
        summary_points = []
        for msg in middle_msgs:
            role = getattr(msg, "role", "unknown")
            content = getattr(msg, "content", "")
            if role == "assistant" and "ACTION:" in content:
                for line in content.splitlines():
                    if line.startswith("ACTION:"):
                        summary_points.append(f"- Step executed: {line.strip()}")
            elif role == "user" and "OBSERVATION:" in content:
                obs = content.replace("OBSERVATION:", "").strip()
                summary_points.append(f"  Result: {obs[:80]}...")

        compressed_content = (
            "SUMMARY OF PRIOR INTERMEDIATE STEPS:\n"
            + "\n".join(summary_points[-6:])
            + "\n(Continuing from recent history...)"
        )

        from .llm_client import ChatMessage
        summary_message = ChatMessage(role="user", content=compressed_content)

        return head_msgs + [summary_message] + tail_msgs


# ---------------------------------------------------------------------------
# 5. Response & Observation Cache
# ---------------------------------------------------------------------------

@dataclass
class CacheEntry:
    value: Any
    created_at: float
    tokens_estimate: int
    cost_estimate_usd: float


class ResponseCache:
    """In-memory cache for deterministic tool executions and LLM query responses."""

    def __init__(self, max_entries: int = 500):
        self._max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self.hits: int = 0
        self.misses: int = 0
        self.tokens_saved: int = 0
        self.cost_saved_usd: float = 0.0

    @staticmethod
    def hash_key(namespace: str, data: Any) -> str:
        """Generate a SHA-256 fingerprint for a cached item."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        raw_key = f"{namespace}:{serialized}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached result if present."""
        entry = self._cache.get(key)
        if entry is not None:
            self.hits += 1
            self.tokens_saved += entry.tokens_estimate
            self.cost_saved_usd = round(self.cost_saved_usd + entry.cost_estimate_usd, 6)
            return entry.value
        self.misses += 1
        return None

    def set(
        self,
        key: str,
        value: Any,
        tokens_estimate: int = 0,
        cost_estimate_usd: float = 0.0,
    ) -> None:
        """Store result in cache with LRU-like eviction if capacity reached."""
        import time
        if len(self._cache) >= self._max_entries:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            tokens_estimate=tokens_estimate,
            cost_estimate_usd=cost_estimate_usd,
        )

    def clear(self) -> None:
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) if total_requests > 0 else 0.0
        return {
            "entries_count": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4),
            "tokens_saved": self.tokens_saved,
            "cost_saved_usd": self.cost_saved_usd,
        }
