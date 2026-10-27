"""Agent module for AI DevOps Assistant.

Adheres strictly to contracts/agent_contract.md.
Prohibits direct access to database, secrets, or cloud provider APIs.
"""

from .config import AgentConfig
from .credit_optimizer import (
    BudgetExceededException,
    ComplexityTier,
    ModelPricing,
    ModelRoute,
    PromptPruner,
    ResponseCache,
    SemanticComplexityRouter,
    TokenBudgetManager,
    get_model_pricing,
)
from .interface import (
    ActorContext,
    AgentAction,
    AgentConstraints,
    AgentContext,
    AgentRequest,
    AgentResult,
    AgentRuntime,
    AgentStatus,
    RepositoryContext,
)
from .llm_client import (
    ChatMessage,
    DeepSeekClient,
    DeepSeekFlashClient,
    DeepSeekProClient,
    LLMResponse,
    MultiModelLLMClient,
    NemotronClient,
    NemotronLightningClient,
    NemotronSuperVLClient,
)
from .memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryManager,
    MemoryTier,
)
from .mock_agent import MockAgent
from .orchestrator import (
    AgentCapability,
    AgentOrchestrator,
    AgentRole,
    HandoffRequest,
)
from .planner import (
    AgentPlan,
    SubTask,
    TaskDecomposer,
)
from .react_agent import ReActAgent
from .tracer import (
    AgentTrace,
    AgentTracer,
    TraceStep,
)

__all__ = [
    # Contracts & Interfaces
    "AgentStatus",
    "AgentContext",
    "AgentConstraints",
    "AgentRequest",
    "AgentAction",
    "AgentResult",
    "AgentRuntime",
    "RepositoryContext",
    "ActorContext",
    # Agents
    "MockAgent",
    "ReActAgent",
    # Configuration
    "AgentConfig",
    # LLM Clients & Responses
    "ChatMessage",
    "LLMResponse",
    "MultiModelLLMClient",
    "DeepSeekClient",
    "NemotronClient",
    "NemotronLightningClient",
    "NemotronSuperVLClient",
    "DeepSeekFlashClient",
    "DeepSeekProClient",
    # Credit Efficiency & Optimization
    "ModelPricing",
    "ModelRoute",
    "TokenBudgetManager",
    "PromptPruner",
    "ResponseCache",
    "SemanticComplexityRouter",
    "ComplexityTier",
    "BudgetExceededException",
    "get_model_pricing",
    # Planning & Multi-Agent Orchestration
    "TaskDecomposer",
    "AgentPlan",
    "SubTask",
    "AgentOrchestrator",
    "AgentRole",
    "AgentCapability",
    "HandoffRequest",
    # Tracer & Memory
    "AgentTracer",
    "AgentTrace",
    "TraceStep",
    "MemoryManager",
    "MemoryTier",
    "MemoryCategory",
    "MemoryEntry",
]
