# Agent Subsystem

**Status:** ReAct Reasoning Engine & Multi-Agent Architecture Active  
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

## Subsystem Components
- **`interface.py`**: Canonical Pydantic schemas (`AgentContext`, `AgentRequest`, `AgentAction`, `AgentResult`, `AgentStatus`).
- **`react_agent.py`**: Multi-step ReAct reasoning loop (Thought -> Action -> Observation -> Final Answer) with approval gating.
- **`llm_client.py`**: Decoupled LLM provider client using standard library `urllib` (zero forbidden dependencies) for DeepSeek and Nemotron endpoints.
- **`tracer.py`**: Fine-grained distributed tracer tracking step latencies, token consumption estimates, and W3C trace IDs.
- **`memory.py`**: Unified 3-tier memory engine (Short-Term run scratchpad, Conversation session memory, and Project persistent memory) with automated secret redaction.
- **`planner.py`**: Task decomposition engine breaking complex goals into dependency-linked sub-tasks (`AgentPlan`, `SubTask`).
- **`orchestrator.py`**: Role-based agent coordinator managing dynamic role selection and inter-agent handoffs (`REVIEWER`, `DEPLOYER`, `DIAGNOSTICIAN`, `MONITOR`, `PLANNER`).
- **`evaluation.py` & `golden_datasets.py`**: Offline evaluation harness and golden benchmark cases for regression testing and accuracy scoring.
- **`mock_agent.py`**: Deterministic offline stub agent for contract adherence and baseline unit tests.

## Dual-Model Strategy
- **DeepSeek (`deepseek-chat`)**: High-throughput routine reasoning (PR code reviews, test analysis, syntax verification).
- **NVIDIA Nemotron (on Nebius AI Cloud)**: High-complexity operational reasoning (release risk quantification, incident root cause diagnosis, rollback orchestration).

