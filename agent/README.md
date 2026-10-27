# Agent Subsystem

**Status:** Multi-Agent Orchestration & Credit Optimization Active  
**Canonical Contract:** `contracts/agent_contract.md`  

## Architectural Invariants
1. **Isolated Execution:** The agent operates strictly through the `AgentRuntime` interface:
   ```python
   agent.run(goal, context, tools, permissions) -> AgentResult
   ```
2. **Zero Direct Access:**
   - **No PostgreSQL:** The agent must never import `app.db` or establish database connections.
   - **No Cloud SDKs:** The agent must never import GitHub, Vercel, Render, or Nebius SDKs.
   - **No Secrets:** The agent never receives raw credentials or deployment tokens.
3. **Controlled Tool Invocation:** All actions must be emitted as `AgentAction` objects validated and dispatched by the Platform Tool Registry.
4. **Standard Library Network Transport:** All LLM communication uses `urllib.request` inside `asyncio.to_thread` with zero external HTTP client dependencies (`requests`, `httpx`, `aiohttp` are strictly forbidden).

---

## Subsystem Components

- **`interface.py`**: Canonical Pydantic schemas (`AgentContext`, `AgentRequest`, `AgentAction`, `AgentResult`, `AgentStatus`).
- **`credit_optimizer.py`**: Enterprise credit and token optimization:
  - `ModelPricing`: Live pricing registries for DeepSeek ($0.14 input, $0.28 output / 1M) and NVIDIA Nemotron on Nebius ($1.00 input, $3.00 output / 1M).
  - `TokenBudgetManager`: Real-time token consumption and USD cost accounting with warning thresholds and hard stops.
  - `PromptPruner`: Sliding-window history compression and smart truncation of large diffs/logs, reducing prompt token overhead by up to 80%.
  - `ResponseCache`: In-memory SHA-256 fingerprint cache for tool observations and deterministic model completions.
  - `SemanticComplexityRouter`: Classifies goals/subtasks into `FAST` (DeepSeek) or `REASONING` (Nemotron).
- **`llm_client.py`**: Multi-model OpenAI-compatible client supporting DeepSeek and NVIDIA Nemotron via Nebius AI Cloud with token and cost tracking.
- **`orchestrator.py`**: Enterprise multi-agent coordinator (`AgentOrchestrator`) managing specialized personas, model routing, and dynamic handoffs:
  - `REVIEWER`: Analyzes code quality, diffs, and security vulnerabilities.
  - `DEPLOYER`: Executes rollout sequences, pre-flight safety gates, health checks, and rollbacks.
  - `DIAGNOSTICIAN`: Analyzes logs, metrics, error traces, and conducts deep root-cause post-mortems using Nemotron.
  - `MONITOR`: Continuous telemetry checks and health verification using DeepSeek.
  - `PLANNER`: Strategic goal decomposition and cross-agent synthesis.
- **`planner.py`**: Task decomposition engine (`TaskDecomposer`, `AgentPlan`, `SubTask`) breaking high-level objectives into dependency-linked subtasks with role and model assignments.
- **`react_agent.py`**: Multi-step ReAct reasoning loop (Thought -> Action -> Observation -> Final Answer) with approval gating, observation pruning, and budget guardrails.
- **`tracer.py`**: Distributed execution tracer tracking step latencies, token consumption estimates, and W3C trace IDs.
- **`memory.py`**: Unified 3-tier memory engine (Short-Term run scratchpad, Conversation session memory, and Project persistent memory) with automated secret redaction.
- **`evaluation.py` & `golden_datasets.py`**: Offline evaluation harness and golden benchmark cases for regression testing and accuracy scoring.
- **`mock_agent.py`**: Deterministic offline stub agent for contract adherence and baseline unit tests.

---

## Dual-Model Strategy: DeepSeek + NVIDIA Nemotron on Nebius

| Capability / Task | Target Model | Provider / Endpoint | Rationale & Credit Efficiency |
| :--- | :--- | :--- | :--- |
| **Diff & Lint Parsing** | `deepseek-chat` | DeepSeek API | $0.14 / 1M tokens. Blazing fast, low-cost token consumption. |
| **Unit Test Evaluation** | `deepseek-chat` | DeepSeek API | Structured deterministic test output evaluation. |
| **Rollout Execution** | `deepseek-chat` | DeepSeek API | Sequential tool calls conforming to rigid parameters. |
| **Telemetry Health Check** | `deepseek-chat` | DeepSeek API | High throughput periodic metric polling. |
| **Security Audit & CVEs** | `nvidia/nemotron-4-340b-instruct` | Nebius AI Cloud | Deep multi-step reasoning, threat modeling, and vulnerability correlation. |
| **Incident Root Cause** | `nvidia/nemotron-4-340b-instruct` | Nebius AI Cloud | Complex causal inference across distributed log traces. |
| **Rollback Risk Assessment** | `nvidia/nemotron-4-340b-instruct` | Nebius AI Cloud | Risk scoring and architectural dependency evaluation. |

---

## Credit Efficiency & Cost Controls

```python
from agent import AgentOrchestrator, AgentConfig, TokenBudgetManager

config = AgentConfig(
    max_tokens_budget=50_000,
    max_cost_usd_budget=0.25,     # Hard limit at $0.25 USD
    enable_prompt_pruning=True,   # Compress scratchpad observations
    enable_response_cache=True,   # Deduplicate tool results
)

orchestrator = AgentOrchestrator(config=config)
result = await orchestrator.orchestrate(goal, context, tools, permissions)

print(result.metrics["total_cost_usd"])
print(result.metrics["tokens_by_model"])
print(result.metrics["tokens_saved_by_cache"])
```
