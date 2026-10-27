"""Agent runtime configuration.

Isolated from backend app.core.config to respect agent/platform boundary.
The agent only reads its own config — never touches backend secrets.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentConfig:
    """Configuration for the ReAct and Multi-Agent Orchestration runtime."""

    # --- Primary / Default LLM Settings ---
    model_name: str = "deepseek-chat"
    api_base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.1
    max_tokens: int = 4096

    # --- Dual Model Routing: DeepSeek & NVIDIA Nemotron on Nebius ---
    preferred_fast_model: str = "deepseek-chat"
    deepseek_api_base: str = "https://api.deepseek.com/v1"

    preferred_reasoning_model: str = "nvidia/nemotron-4-340b-instruct"
    nebius_api_base: str = "https://api.studio.nebius.ai/v1"
    nemotron_model_name: str = "nvidia/nemotron-4-340b-instruct"
    nebius_api_key: Optional[str] = None

    # --- Agent Loop Guardrails ---
    default_max_steps: int = 20
    default_timeout_seconds: int = 300

    # --- Multi-Agent Orchestration ---
    enable_multi_agent: bool = True
    default_orchestrator_max_rounds: int = 5
    enable_auto_handoffs: bool = True

    # --- Credit Efficiency & Token Budgeting ---
    max_tokens_budget: int = 60_000
    max_cost_usd_budget: float = 0.50
    warning_budget_threshold_pct: float = 0.80

    # --- Prompt Pruning & Compression ---
    enable_prompt_pruning: bool = True
    max_observation_chars: int = 1500
    max_history_turns: int = 8

    # --- Observation & Response Caching ---
    enable_response_cache: bool = True
    cache_max_entries: int = 500

    # --- Retry Settings ---
    max_retries_per_tool: int = 2
    retry_backoff_seconds: float = 1.0

    # --- Safety & Approval ---
    require_human_approval_for: List[str] = field(default_factory=lambda: [
        "deployment.deploy",
        "deployment.rollback",
    ])
