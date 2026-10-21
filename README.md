# NexOps — AI DevOps Assistant

[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-blue.svg)](docs/architecture.md)
[![Phase](https://img.shields.io/badge/Phase-6%20Complete-green.svg)](docs/development-workflow.md)
[![Agent](https://img.shields.io/badge/Agent-DeepSeek%20ReAct-purple.svg)](agent/react_agent.py)
[![Tests](https://img.shields.io/badge/Tests-51%20Passing-brightgreen.svg)](backend/tests/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-009688.svg)](backend/)
[![React](https://img.shields.io/badge/Frontend-React%20%7C%20TypeScript-61DAFB.svg)](frontend/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791.svg)](docker-compose.yml)

An autonomous, persistent developer control plane that connects GitHub and hosting providers to automate pull request reviews, run tests, assess release risk, orchestrate deployments, continuously monitor production health, diagnose incidents, and execute safe automated rollbacks.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    React + TypeScript SPA                        │
│               (Pipeline Visualizer / Dashboard)                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST + SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                  FastAPI Modular Monolith                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Auth &   │  │ Tool Registry│  │   Event Bus              │  │
│  │ Projects │  │ & Permission │  │   (PostgreSQL-backed)    │  │
│  │ (JWT)    │  │ Guard        │  │                          │  │
│  └──────────┘  └──────┬───────┘  └──────────────────────────┘  │
│                        │                                        │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │              Agent Runtime (Sandboxed)                    │   │
│  │  ┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐    │   │
│  │  │ ReAct   │ │ Memory │ │Planner │ │ Orchestrator │    │   │
│  │  │ Loop    │ │ 3-Tier │ │        │ │ Multi-Agent  │    │   │
│  │  └─────────┘ └────────┘ └────────┘ └──────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────── Tools ──────────────────────────────┐   │
│  │ GitHub │ Tests │ Deploy │ Logs │ Metrics │ Kubernetes   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────── Provider Adapters ─────────────────────┐    │
│  │    Vercel    │     Render     │    Nebius AI Cloud     │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │     16      │
                    └─────────────┘
```

---

## How It Works

1. **A goal arrives** — e.g., "Review PR #42 for security issues" (triggered by a webhook or user action).
2. **The Planner decomposes it** — breaks the goal into ordered sub-tasks: fetch PR → get diff → analyze → summarize.
3. **The Orchestrator routes it** — selects the right specialist: Reviewer for code reviews, Deployer for deployments, Diagnostician for incidents.
4. **The ReAct loop executes** — the agent reasons (via DeepSeek LLM), selects a tool, the platform executes it, and the agent observes the result. This repeats until the agent reaches a conclusion.
5. **Tools run on the platform** — the agent never calls GitHub, Kubernetes, or databases directly. It requests a tool call, the platform checks permissions, executes it, and returns the result with a full audit trail.
6. **Memory captures key findings** — short-term (forgotten after the run), conversation-level (session-scoped), and project-level (permanent across sessions).
7. **Tracer logs every step** — reasoning, tool calls, latency, and token usage for full observability.
8. **A structured result is returned** — `AgentResult` containing status, confidence score, actions taken, and output — ready for the backend to consume and display.

> **Safety:** The agent is sandboxed. It cannot access databases, secrets, or APIs directly. Human approval is required for deployments and rollbacks. AST-level boundary tests enforce this at CI time.

---

## AI Agent Architecture

The agent uses a **ReAct (Reason → Act → Observe)** loop powered by **DeepSeek** with full contract-driven isolation.

### Agent Components

| Component | File | Description |
|-----------|------|-------------|
| **ReAct Agent** | [`agent/react_agent.py`](agent/react_agent.py) | Core reasoning loop — thinks, calls tools, observes results, re-plans |
| **LLM Client** | [`agent/llm_client.py`](agent/llm_client.py) | DeepSeek API client (stdlib-only, no `requests`/`httpx`) |
| **Prompts** | [`agent/prompts.py`](agent/prompts.py) | System prompt + context engineering for tool selection |
| **Memory** | [`agent/memory.py`](agent/memory.py) | 3-tier memory: short-term (per-run), conversation, project (persistent) |
| **Planner** | [`agent/planner.py`](agent/planner.py) | Task decomposition — breaks complex goals into ordered sub-tasks |
| **Orchestrator** | [`agent/orchestrator.py`](agent/orchestrator.py) | Multi-agent routing: Reviewer, Deployer, Diagnostician, Monitor |
| **Tracer** | [`agent/tracer.py`](agent/tracer.py) | Step-by-step tracing with latency, token estimates, and export |
| **Evaluator** | [`agent/evaluation.py`](agent/evaluation.py) | Scores agent runs against golden datasets (trajectory + outcome) |
| **Golden Datasets** | [`agent/golden_datasets.py`](agent/golden_datasets.py) | Test cases for PR review, deployment, and incident scenarios |
| **Config** | [`agent/config.py`](agent/config.py) | Model settings, guardrails, human-approval gates |

### Agent Flow

```
Goal arrives → Planner decomposes into sub-tasks
                    ↓
            Orchestrator selects specialist agent (Reviewer/Deployer/Diagnostician)
                    ↓
            ┌─ DeepSeek THINKS (THOUGHT)
            │         ↓
            │  Selects a tool (ACTION: github.get_diff)
            │         ↓
            │  Platform executes tool → Permission check → Audit log
            │         ↓
            │  Agent reads result (OBSERVATION)
            │         ↓
            │  Memory stores key findings
            │         ↓
            │  Tracer logs step + latency + tokens
            │         ↓
            └─ Loops until → FINAL_ANSWER
                    ↓
            Returns structured AgentResult → Backend consumes it
```

### Guardrails & Safety

- **Human approval required** for `deployment.deploy` and `deployment.rollback`
- **Max step limit** (default: 20 steps) prevents runaway loops
- **Timeout enforcement** (default: 300s)
- **Permission gating** — agent cannot call tools it lacks permissions for
- **Boundary enforcement** — AST-level tests verify agent never imports DB/SDK/HTTP libraries
- **Secret redaction** — memory system strips API keys and tokens before storing

### Tools Catalog

| Tool | Permission | Side Effects | Timeout |
|------|-----------|-------------|---------|
| `github.get_repository` | `repo:read` | No | 15s |
| `github.get_pull_request` | `repo:read` | No | 15s |
| `github.get_diff` | `repo:read` | No | 30s |
| `tests.run` | `test:execute` | No | 180s |
| `deployment.deploy` | `deploy:staging/production` | **Yes** | 60s |
| `deployment.status` | `repo:read` | No | 15s |
| `deployment.logs` | `repo:read` | No | 30s |
| `deployment.rollback` | `deploy:staging/production` | **Yes** | 60s |
| `logs.fetch` | `repo:read` | No | 30s |
| `logs.analyze` | `repo:read` | No | 30s |
| `metrics.collect` | `repo:read` | No | 15s |
| `metrics.analyze` | `repo:read` | No | 15s |
| `kubernetes.get_pods` | `repo:read` | No | 15s |
| `kubernetes.get_pod_logs` | `repo:read` | No | 30s |
| `kubernetes.get_deployments` | `repo:read` | No | 15s |

### Eventual LLM Routing

- **DeepSeek:** Fast, routine code diff parsing, lint verification, and low-latency status checks.
- **NVIDIA Nemotron (on Nebius AI Cloud):** High-order cognitive reasoning, architectural risk analysis, incident triage, and root-cause post-mortems.

---

## Architectural Principles

1. **Modular Monolith:** Clean monolith eliminating distributed systems complexity (no Kubernetes, Kafka, or microservices at runtime).
2. **Strict Agent/Platform Boundary:** The agent is an isolated reasoning runtime that **never** accesses PostgreSQL, secrets, or provider SDKs directly. All operations are mediated through the Platform Tool Registry.
3. **Provider Abstraction:** Unified `DeploymentProvider` interface decoupling deployment workflows from specific hosting backends (Vercel, Render, Nebius AI Cloud).
4. **Contract-First Design:** All communication between the agent, platform, tools, and events is governed by canonical specifications.
5. **Clean Data Layer & Tenant Isolation:** API → Application Services → Repositories → SQLAlchemy → PostgreSQL with strict project-level isolation.

---

## Repository Structure

```
NexOps/
├── agent/                          # Isolated agent runtime (never imports DB/cloud SDKs)
│   ├── react_agent.py              #   ReAct reasoning loop (DeepSeek-powered)
│   ├── llm_client.py               #   DeepSeek API client (stdlib only)
│   ├── prompts.py                  #   System prompt + context engineering
│   ├── memory.py                   #   3-tier memory (short-term, conversation, project)
│   ├── planner.py                  #   Task decomposition into sub-goals
│   ├── orchestrator.py             #   Multi-agent routing & handoffs
│   ├── tracer.py                   #   Step tracing (latency, tokens, reasoning)
│   ├── evaluation.py               #   Agent evaluation harness
│   ├── golden_datasets.py          #   Golden test cases (PR review, deploy, incident)
│   ├── config.py                   #   Agent settings & guardrails
│   ├── interface.py                #   Canonical data shapes (AgentResult, etc.)
│   └── mock_agent.py               #   Phase 0 stub agent for testing
│
├── backend/                        # FastAPI modular monolith
│   ├── alembic/                    #   Versioned database migrations (001, 002, 003, 004)
│   ├── app/
│   │   ├── api/v1/                 #     REST routes (/health, /auth, /projects, /github, /events, /agent, /reviews, /tests)
│   │   ├── core/                   #     Config, security (JWT, bcrypt, AES Fernet)
│   │   ├── db/                     #     Session management, models, repositories, constants
│   │   ├── schemas/                #     Pydantic request/response schemas (auth, project, event, review, test_run)
│   │   ├── services/               #     Auth, project, event_bus, github, diff_parser, context_engine, tools, agent_execution, review_service, test_service
│   │   ├── tools/                  #     Tool implementations (GitHub, K8s, logs, metrics, deploy, tests)
│   │   └── providers/              #     Deployment provider abstractions
│   └── tests/                      #   51 pytest tests (boundaries, contracts, eval, API, DB, RBAC, migrations, tools, agent, reviews, tests)
│
├── contracts/                      # Canonical contracts (6 specifications)
│   ├── agent_contract.md           #   Agent invocation lifecycle
│   ├── tool_contract.md            #   Tool registry, schemas, permissions
│   ├── event_contract.md           #   16 canonical lifecycle events
│   ├── deployment_contract.md      #   10-state deployment FSM
│   ├── memory_contract.md          #   3-tier memory architecture
│   └── review_contract.md          #   Structured code review schemas
│
├── docs/                           # Architecture documentation
│   ├── architecture.md             #   System architecture blueprint
│   ├── development-workflow.md     #   15-phase implementation roadmap
│   └── database-architecture.md    #   Full database specification
│
├── frontend/                       # React + TypeScript SPA (Developer Console)
│   └── src/
│       ├── api/                    #   Typed API client (auth, projects, github, events, agent, reviews, tests)
│       ├── types/                  #   Contract-aligned TypeScript types
│       └── App.tsx                 #   Tabbed Developer Console UI (Projects, GitHub, PRs, AI Reviews, Test Runner, Events, RBAC, Keys)
│
├── scripts/verify_contracts.py     # Automated contract consistency checker
├── docker-compose.yml              # PostgreSQL + Backend + Frontend orchestration
└── .env.example                    # Environment configuration template
```

---

## Development Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 0 | Foundation & Architecture | ✅ Complete |
| 1 | Authentication + Projects + Database + RBAC | ✅ Complete |
| — | **Agent Development (all tasks)** | ✅ **Complete** |
| 2 | GitHub Integration (Webhooks, HMAC, EventBus, PRs) | ✅ Complete |
| 3 | Context Engine (Diff Parser, Token Budgeting) | ✅ Complete |
| 4 | Tool Execution Boundary (Gatekeeper Pipeline, RBAC, Audit) | ✅ Complete |
| 5 | Agent Runtime Integration (ReAct Wired to Tools & EventBus) | ✅ Complete |
| 6 | Review + Testing Engines (Risk Gates, Test Runner, PR Comments) | ✅ Complete |
| 7 | Risk Assessment & Guardrails | ⬜ Next Up |
| 8 | Deployment Adapters (Vercel, Render, Nebius) | ⬜ Designed |
| 9 | Health Monitoring & Probes | ⬜ Designed |
| 10 | Incident Recovery & Rollbacks | ⬜ Designed |
| 11 | Semantic Memory (`pgvector`) & Evals | ⬜ Designed |
| 12 | Nebius AI Cloud & Nemotron Model Routing | ⬜ Designed |
| 13 | React Frontend Console | ✅ Complete |
| 14 | E2E Golden Path Testing & Demo | ⬜ Designed |

---

## Canonical Contracts

| Contract | Description |
|----------|-------------|
| [`agent_contract.md`](contracts/agent_contract.md) | Agent invocation lifecycle (`AgentContext`, `AgentRequest`, `AgentResult`, `AgentAction`, `AgentStatus`) |
| [`tool_contract.md`](contracts/tool_contract.md) | Platform Tool Registry specifications, permission checks, schemas, and audit logging |
| [`event_contract.md`](contracts/event_contract.md) | 16 canonical lifecycle events from `PR_OPENED` to `RECOVERY_COMPLETED` |
| [`deployment_contract.md`](contracts/deployment_contract.md) | `DeploymentProvider` protocol and 10 canonical deployment states |
| [`memory_contract.md`](contracts/memory_contract.md) | Ephemeral short-term, conversation, and project persistent memory tiers |
| [`review_contract.md`](contracts/review_contract.md) | Structured AI code review schemas, finding taxonomies, and severity risk gates |

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local test execution)
- Node.js 20+ (for frontend development)
- DeepSeek API key (for agent — get one at [platform.deepseek.com](https://platform.deepseek.com/api_keys))

### Quick Start with Docker Compose
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Add your DeepSeek API key to .env
# DEEPSEEK_API_KEY=your-key-here

# 3. Build and launch services (PostgreSQL, FastAPI Backend, React Frontend)
docker compose up -d

# 4. Run database migrations
cd backend && alembic upgrade head && cd ..

# 5. Verify backend health
curl http://localhost:8000/health
```

### Run Tests
```bash
# Run full test suite (51 tests)
cd backend && python -m pytest tests/ -v

# Run contract verification
python scripts/verify_contracts.py
```

### Use the Agent (Python)
```python
from agent import ReActAgent

agent = ReActAgent(api_key="sk-your-deepseek-key")
result = await agent.run(
    goal="Review PR #42 for security issues",
    context=context,
    tools=["github.get_pull_request", "github.get_diff"],
    permissions=["repo:read"],
)

print(result.status)      # COMPLETED
print(result.confidence)  # 0.85
print(result.output)      # {"summary": "...", "risk": "LOW"}
```

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | No |
| `GET` | `/api/v1/health` | API v1 health check | No |
| `POST` | `/api/v1/auth/register` | Create account | No |
| `POST` | `/api/v1/auth/login` | Get JWT token | No |
| `GET` | `/api/v1/auth/me` | Get current user profile | Bearer |
| `POST` | `/api/v1/projects` | Create project | Bearer |
| `GET` | `/api/v1/projects` | List user projects | Bearer |
| `GET` | `/api/v1/projects/{id}` | Project detail | Bearer |
| `DELETE` | `/api/v1/projects/{id}` | Soft delete project | Bearer (Owner) |
| `GET` | `/api/v1/projects/{id}/members` | List project members & roles | Bearer |
| `POST` | `/api/v1/projects/{id}/members` | Add/invite member with role | Bearer (Owner/Maintainer) |
| `PATCH` | `/api/v1/projects/{id}/members/{user_id}` | Update member role | Bearer (Owner) |
| `DELETE` | `/api/v1/projects/{id}/members/{user_id}` | Remove member | Bearer (Owner) |
| `POST` | `/api/v1/projects/{id}/api-keys` | Generate scoped API key | Bearer (Owner/Maintainer) |
| `GET` | `/api/v1/projects/{id}/api-keys` | List active API keys | Bearer |
| `DELETE` | `/api/v1/projects/{id}/api-keys/{key_id}` | Revoke API key | Bearer (Owner/Maintainer) |
| `POST` | `/api/v1/projects/{id}/github/connect` | Connect GitHub repo via App/PAT | Bearer (Owner/Maintainer) |
| `GET` | `/api/v1/projects/{id}/github/status` | Get GitHub connection status | Bearer |
| `DELETE` | `/api/v1/projects/{id}/github/disconnect` | Disconnect GitHub repository | Bearer (Owner) |
| `GET` | `/api/v1/projects/{id}/github/pulls` | List ingested pull requests | Bearer |
| `POST` | `/api/v1/projects/{id}/github/pulls/{pull_number}/review` | Trigger autonomous PR review | Bearer |
| `GET` | `/api/v1/projects/{id}/github/pulls/{pull_number}/reviews` | List past reviews for pull request | Bearer |
| `GET` | `/api/v1/projects/{id}/reviews` | List all reviews for project | Bearer |
| `GET` | `/api/v1/projects/{id}/reviews/{review_id}` | Get review detail with findings | Bearer |
| `POST` | `/api/v1/projects/{id}/tests/run` | Trigger automated test suite run | Bearer |
| `GET` | `/api/v1/projects/{id}/tests/runs` | List test runs for project or PR | Bearer |
| `GET` | `/api/v1/projects/{id}/tests/runs/{run_id}` | Get test run detail and test cases | Bearer |
| `POST` | `/api/v1/projects/{id}/github/webhook` | Ingest GitHub webhook events (HMAC-SHA256 verified) | GitHub Signature |
| `GET` | `/api/v1/projects/{id}/events` | Ingested platform event feed (EventBus) | Bearer |
| `POST` | `/api/v1/agent/run` | Execute ReAct agent on arbitrary DevOps goal | Bearer / API Key |
| `POST` | `/api/v1/agent/run-pr` | Execute ReAct agent directly on Pull Request context | Bearer / API Key |

---

## License

MIT
