# Architecture Specification: AI DevOps Assistant

**Document Version:** 1.0.0  
**Status:** Architecture Blueprint  
**Design Paradigm:** Modular Monolith with Strict Contract-Driven Agent Boundaries  

---

## 1. System Overview

The **AI DevOps Assistant** is an autonomous developer control plane engineered for modern cloud and application lifecycles. It bridges developer pull requests with runtime deployment environments. Rather than acting as a simple chatbot, the Assistant operates as a persistent operational agent that:
- Ingests pull requests and code modifications.
- Executes automated, syntax- and vulnerability-aware code reviews.
- Triggers isolated test suites and interprets failures.
- Quantifies release risk using hybrid LLM reasoning (DeepSeek for fast tasks, NVIDIA Nemotron on Nebius AI Cloud for complex reasoning).
- Deploys workloads across disparate hosting providers (Vercel, Render, Nebius AI Cloud).
- Monitors post-deployment health metrics and logs.
- Detects incidents, diagnoses root causes from logs and diffs, and orchestrates safe rollbacks.

### Design Principles:
- **Modular Monolith:** A single cohesive codebase and deployable backend, avoiding microservice operational overhead, Kubernetes, or distributed message queues in early development.
- **Contract-First Boundary:** The Agent subsystem is strictly decoupled from platform internals, operating only through formal schemas and the Tool Registry.
- **Provider Agnosticism:** Deployments adhere to an abstract provider protocol, preventing cloud vendor lock-in.
- **Defense in Depth:** The agent has zero direct network or database access to cloud providers, secrets, or internal persistence.

---

## 2. Major Components

```
+-----------------------------------------------------------------------------------+
|                               USER / DEVELOPER                                    |
+-----------------------------------------------------------------------------------+
                                   | HTTP / SSE
                                   v
+-----------------------------------------------------------------------------------+
|                            REACT FRONTEND (SPA)                                   |
|   - Real-time Pipeline Dashboard  - Review Feed  - Incident & Rollback Console   |
+-----------------------------------------------------------------------------------+
                                   | REST / SSE
                                   v
+-----------------------------------------------------------------------------------+
|                        FASTAPI BACKEND (MODULAR MONOLITH)                         |
|                                                                                   |
|  +---------------------+  +----------------------+  +--------------------------+  |
|  |   API Layer (v1)    |  |  Event Dispatcher    |  |  Auth & Project Service  |  |
|  +---------------------+  +----------------------+  +--------------------------+  |
|  |   Review Service    |  |  Deployment Service  |  |  Incident & Health Probe |  |
|  +---------------------+  +----------------------+  +--------------------------+  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                       TOOL REGISTRY & PERMISSION GUARD                      |  |
|  |  [Validation] -> [RBAC / Capability Check] -> [Audit Log] -> [Execution]    |  |
|  +-----------------------------------------------------------------------------+  |
|         |                                      |                                  |
|         v (Controlled Tool Calls)              v                                  |
|  +---------------------------+   +---------------------------------------------+  |
|  |      AGENT RUNTIME        |   |             PROVIDER ADAPTERS               |  |
|  |  (Planner / Reasoning)    |   |  - VercelAdapter (Frontend / Edge)          |  |
|  |  - DeepSeek Router        |   |  - RenderAdapter (Backend / Containers)     |  |
|  |  - Nemotron on Nebius     |   |  - NebiusAdapter (GPU / Model Endpoints)    |  |
|  +---------------------------+   +---------------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                   | SQLAlchemy / Alembic
                                   v
+-----------------------------------------------------------------------------------+
|                              POSTGRESQL DATABASE                                  |
|  - Projects, Users, API Keys  - Event Log  - Deployments & Incidents  - Memory    |
+-----------------------------------------------------------------------------------+
```

### Component Roles:
1. **React Frontend:** User-facing dashboard providing visualization of active PR reviews, test run status, deployment states, risk matrices, and one-click rollback approval controls.
2. **FastAPI Modular Monolith:** Central API, domain services, orchestration workflows, and event bus.
3. **Agent Runtime:** Isolated execution context executing multi-step reasoning cycles to fulfill high-level goals.
4. **Tool Registry & Permission Guard:** Security middleware that intercepts, authorizes, validates, executes, and audits every tool call.
5. **Deployment Service & Adapters:** Uniform abstraction layer managing deployment lifecycles across Vercel, Render, and Nebius AI Cloud.
6. **PostgreSQL:** Canonical relational persistence and event store.

---

## 3. Dependency Direction

Dependencies strictly point **inward** toward domain abstractions and contracts:

```
[ Frontend ]
     |
     v
[ FastAPI API Routes ]
     |
     v
[ Application / Domain Services ]
     |                                    \
     v                                     v
[ Tool Registry / Contracts ] <---- [ Agent Runtime ]
     |
     +------------+------------+
     |            |            |
     v            v            v
[ Adapters ] [ DB / Repos ] [ External SDKs ]
```

### Dependency Rules:
- The **Agent Runtime** depends ONLY on `contracts/` and `agent/` abstractions. It NEVER imports from `app.models`, `app.db`, or third-party cloud SDKs.
- The **API Layer** depends on **Domain Services**.
- **Domain Services** implement business operations, invoke the Agent Runtime via `agent.run(...)`, and execute tools via the **Tool Registry**.
- **Adapters** implement the `DeploymentProvider` contract defined in `contracts/deployment_contract.md`.

---

## 4. Agent / Platform Boundary

The Agent is fundamentally an untrusted planner operating in a sandbox:
- **No Direct Persistence:** The Agent cannot read or write to PostgreSQL. If it needs memory, it calls the `memory.retrieve` or `memory.record` tool.
- **No Direct Network Access:** The Agent cannot issue outbound HTTP requests to GitHub, Vercel, Render, or Nebius. It must invoke namespaced tools (e.g., `github.get_pull_request`).
- **No Secrets Exposure:** Environment variables containing provider tokens (`GITHUB_TOKEN`, `VERCEL_TOKEN`, `RENDER_API_KEY`, `NEBIUS_API_KEY`) remain strictly inside the backend platform's memory space and are never fed into LLM prompts.
- **State Inversion:** The agent does not persist its own state. The platform initiates `agent.run(goal, context, tools, permissions)` and handles state persistence upon receiving `AgentResult` or discrete `AgentAction` yields.

---

## 5. Tool Execution Boundary

Every tool requested by an agent passes through a 5-step gatekeeper pipeline:

```
Agent Action -> [ 1. Registry Lookup ]
             -> [ 2. Schema Validation (Input) ]
             -> [ 3. Permission & Policy Gate ]
             -> [ 4. Platform Execution & Audit Log ]
             -> [ 5. Schema Validation (Output) ] -> Agent Result Envelope
```

1. **Registry Lookup:** Verifies the tool name is recognized and active.
2. **Input Validation:** Compares parameters against the tool's JSON Schema.
3. **Permission Gate:** Verifies `AgentContext.permissions` contains the required permission for the tool and environment.
4. **Execution & Audit:** Executes platform logic, records start time, duration, user ID, trace ID, and inputs.
5. **Output Normalization:** Formats return data or errors into `ToolExecutionEnvelope` with deterministic retry flags.

---

## 6. Deployment Abstraction

The system treats all deployments identically regardless of target provider.

### The `DeploymentProvider` Protocol:
- `deploy(request: DeploymentRequest) -> DeploymentResponse`
- `get_status(deployment_id: str) -> DeploymentStatusResponse`
- `get_logs(deployment_id: str, tail: int) -> DeploymentLogsResponse`
- `rollback(request: RollbackRequest) -> RollbackResponse`

### Adapter Implementations:
- **`VercelAdapter`:** Manages frontend applications, serverless functions, preview URLs, and instantaneous alias switching for zero-downtime rollbacks.
- **`RenderAdapter`:** Manages full-stack Web Services and worker processes with health check monitoring.
- **`NebiusAdapter`:** Manages dedicated GPU instances, model serving containers, and AI inference endpoints on Nebius AI Cloud.

All adapters normalize external statuses into the 10 canonical deployment states: `PENDING`, `BUILDING`, `TESTING`, `APPROVED`, `DEPLOYING`, `HEALTH_CHECK`, `SUCCESS`, `FAILED`, `ROLLING_BACK`, `ROLLED_BACK`.

---

## 7. Event Flow

The platform utilizes an in-process, relational-backed Event Bus:
1. An external trigger occurs (e.g. GitHub webhook or manual deploy command).
2. The platform commits an immutable event to the `events` table in PostgreSQL.
3. Internal domain listeners handle the event asynchronously.
4. Downstream state changes (e.g. `DEPLOYMENT_COMPLETED`, `HEALTH_CHECK_FAILED`) emit subsequent events.
5. The frontend subscribes to real-time events via Server-Sent Events (SSE).

```
Webhook / User Action
        |
        v
+------------------+
| API Controller   |
+--------+---------+
         | emits
         v
+------------------+     persists     +--------------------+
|  Event Bus       | ---------------> | PostgreSQL Events  |
+--------+---------+                  +--------------------+
         | notifies
         +-----------------------------+
         |                             |
         v                             v
+------------------+          +------------------+
|  Domain Handler  |          | Frontend (SSE)   |
|  (e.g., Agent)   |          +------------------+
+------------------+
```

---

## 8. Data Flow

### Example: Automated PR Review & Pre-Deploy Risk Gate
```
1. Developer pushes PR to GitHub.
2. GitHub sends webhook -> FastAPI Backend.
3. Backend emits PR_OPENED event.
4. Review Service constructs AgentContext with permissions: ["repo:read", "test:execute"].
5. Backend calls agent.run("Perform security and stability review for PR #42", ...).
6. Agent yields AgentAction: github.get_diff(pull_number=42).
7. Platform validates, fetches diff via GitHub API, returns to Agent.
8. Agent yields AgentAction: tests.run(commit_sha="a1b2c3d").
9. Platform runs tests in runner, returns results to Agent.
10. Agent synthesizes findings and returns AgentResult with ReviewResult.
11. Platform saves ReviewResult to PostgreSQL, posts comments to GitHub PR, and emits REVIEW_COMPLETED.
```

---

## 9. Security Boundaries

1. **Authentication & Authorization:**
   - Platform users authenticate via JWT / Session tokens.
   - RBAC governs user capabilities (`Admin`, `Developer`, `Viewer`).
2. **Execution Sandboxing:**
   - Tool execution runs strictly inside the platform container with non-root privileges.
3. **Secret Isolation:**
   - Secrets are loaded into memory via environment variables or a secret store.
   - Secrets are NEVER injected into LLM contexts or tool parameters.
4. **Guardrail Escalation:**
   - Production actions (`deploy:production`, `deployment.rollback`) require explicit human sign-off unless automated emergency recovery policies are active.
5. **Auditing:**
   - All tool executions, agent reasoning steps, and deployment state changes are permanently logged with immutable `trace_id` links.

---

## 10. Future Extension Points

While maintaining a modular monolith in Phase 0, the architecture is designed to accommodate clean horizontal evolution:
- **Phase 11 (Semantic Memory):** Integration of `pgvector` in PostgreSQL for vector embeddings, similarity search, and automated retrieval of past incident resolutions.
- **Phase 12 (Multi-Model Routing):** Dynamic routing between DeepSeek (for routine diff parsing) and NVIDIA Nemotron hosted on Nebius AI Cloud (for high-risk architectural analysis and incident diagnosis).
- **Worker Process Isolation:** The internal event dispatcher can cleanly transition to an external broker (e.g. Celery / Redis / RabbitMQ) without changing domain services or contracts.
- **Multi-Tenant Org Partitioning:** Strict `project_id` scoping in contracts guarantees immediate readiness for multi-tenant SaaS deployment.
