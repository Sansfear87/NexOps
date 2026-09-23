# Agent Subsystem

**Status:** Phase 0 Architecture Placeholder  
**Canonical Contract:** `contracts/agent_contract.md`  

## Architectural Invariants
1. **Isolated Execution:** The agent operates strictly through the `AgentRuntime` interface:
   ```python
   agent.run(goal, context, tools, permissions) -> AgentResult
   ```
2. **Zero Direct Access:**
   - **No PostgreSQL:** The agent must never import `app.db` or establish database connections.
   - **No Cloud SDKs:** The agent must never import GitHub, Vercel, Render, or Nebius SDKs.
   - **No Secrets:** The agent never receives API keys or deployment tokens.
3. **Controlled Tool Invocation:** All actions must be emitted as `AgentAction` objects validated and dispatched by the Platform Tool Registry.

## Implementation Roadmap
- **Phase 0:** Interface & Mock Agent (`agent/mock_agent.py`)
- **Phase 5:** ReAct Execution Loop & Runtime Engine
- **Phase 6:** Code Review & Test Analysis Planners
- **Phase 10:** Incident Triage & Diagnosis Planners
- **Phase 12:** Dynamic Model Routing (DeepSeek for fast tasks, NVIDIA Nemotron on Nebius for complex reasoning)
