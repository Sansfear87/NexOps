"""Agent runtime configuration.

Isolated from backend app.core.config to respect agent/platform boundary.
The agent only reads its own config — never touches backend secrets.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class AgentConfig:
    """Configuration for the DeepSeek-powered ReAct agent."""

    # --- LLM Settings ---
    model_name: str = "deepseek-chat"
    api_base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.1
    max_tokens: int = 4096

    # --- Agent Loop Guardrails ---
    default_max_steps: int = 20
    default_timeout_seconds: int = 300

    # --- Retry Settings ---
    max_retries_per_tool: int = 2
    retry_backoff_seconds: float = 1.0

    # --- Safety ---
    require_human_approval_for: List[str] = field(default_factory=lambda: [
        "deployment.deploy",
        "deployment.rollback",
    ])
