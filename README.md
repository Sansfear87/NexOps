# AI DevOps Assistant

[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-blue.svg)](docs/architecture.md)
[![Status](https://img.shields.io/badge/Phase-Phase%201%20Database%20Architecture-green.svg)](docs/database-architecture.md)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-009688.svg)](backend/)
[![React](https://img.shields.io/badge/Frontend-React%20%7C%20TypeScript-61DAFB.svg)](frontend/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791.svg)](docker-compose.yml)

An autonomous, persistent developer control plane built for hackathons and modern cloud deployments. It connects GitHub and hosting providers to automate pull request reviews, run tests, assess release risk, orchestrate deployments, continuously monitor production health, diagnose incidents, replan, and execute safe automated rollbacks.

---

## Eventual AI Architecture

- **DeepSeek:** Fast, routine code diff parsing, lint verification, and low-latency status checks.
- **NVIDIA Nemotron:** High-order cognitive reasoning, architectural risk analysis, incident triage, and root-cause post-mortems.
- **Nebius AI Cloud:** Dedicated GPU inference infrastructure and model serving hosting.

---

## Architectural Principles

1. **Modular Monolith:** Built initially as a clean modular monolith to eliminate distributed systems complexity (no Kubernetes, Kafka, or microservices).
2. **Strict Agent/Platform Boundary:** The agent is an isolated reasoning runtime that **never** accesses PostgreSQL, secrets, or provider SDKs directly. All operations are mediated through the Platform Tool Registry.
3. **Provider Abstraction:** Unified `DeploymentProvider` interface decoupling deployment workflows from specific hosting backends (Vercel, Render, Nebius AI Cloud).
4. **Contract-First Design:** All communication between the agent, platform, tools, and events is governed by canonical specifications.
5. **Clean Data Layer & Tenant Isolation:** API -> Application Services -> Repositories -> SQLAlchemy -> PostgreSQL with strict project-level isolation.

---

## Database Architecture (`docs/database-architecture.md`)

The comprehensive database architecture spans the full 15-phase lifecycle while keeping migrations strictly phase-gated:

- **Full Lifecycle Specification:** Detailed entity schemas, cardinalities, constraints, indexing strategies, JSONB policies, and soft-delete rules are documented in [`docs/database-architecture.md`](docs/database-architecture.md).
- **Phase 1 Implemented Entities:**
  - `users` (developer accounts, email index, superuser flags)
  - `auth_accounts` (credential accounts, bcrypt hashes, OAuth provider links)
  - `sessions` (server-managed high-entropy session tokens with revocation and expiry)
  - `projects` (project organizational units with soft-archive support)
  - `project_members` (multi-user RBAC memberships with unique constraints)
  - `audit_logs` (immutable event and security compliance ledger)
- **Future Designed Entities:**
  - Phase 2: `github_connections`, `repositories`, `pull_requests`, `pull_request_files`, `webhook_events`
  - Phase 4/5: `agent_runs`, `agent_steps`, `tool_calls`, `agent_failures`
  - Phase 6/7: `reviews`, `review_findings`, `tests`, `test_runs`, `test_results`
  - Phase 8: `deployments`, `deployment_events`, `deployment_artifacts`
  - Phase 9/10: `health_checks`, `incidents`, `incident_events`
  - Phase 11: `conversations`, `messages`, `memories`, `memory_embeddings`, `evaluations`, `evaluation_cases`, `evaluation_runs`, `evaluation_results`

---

## Repository Structure

```
ai-devops-assistant/
├── frontend/             # React + TypeScript SPA developer dashboard
│   ├── src/api/          # Typed API client pipeline (client.ts, auth.ts, projects.ts)
│   └── src/App.tsx       # Phase 0 contract dashboard + Phase 1 data pipeline UI
├── backend/              # FastAPI modular monolith (API, services, DB repositories)
│   ├── alembic/          # Versioned database schema migrations (001_phase1_auth_and_projects.py)
│   ├── app/
│   │   ├── api/v1/       # REST routes (/health, /auth, /projects)
│   │   ├── core/         # Config and bcrypt cryptographic security
│   │   ├── db/           # Session management, declarative models, and repositories
│   │   ├── schemas/      # Pydantic request/response validation schemas
│   │   ├── services/     # Application & domain services (AuthService, ProjectService)
│   │   ├── tools/        # Tool registry and permission gatekeeper
│   │   └── providers/    # Deployment provider abstractions
│   └── tests/            # pytest suite (17 tests covering boundaries, contracts, DB, APIs, migration)
├── agent/                # Isolated agent runtime interfaces (never imports DB/cloud SDKs)
├── contracts/            # Canonical contracts (agent, tool, event, deployment, memory, review)
├── docs/                 # Architectural blueprints and database architecture specification
├── scripts/              # Verification and utility scripts (verify_contracts.py)
├── docker/               # Container Dockerfiles (backend, frontend)
├── .env.example          # Environment configuration template
├── .gitignore            # Git ignore specification
├── README.md             # Project documentation (this file)
└── docker-compose.yml    # PostgreSQL, FastAPI, and React orchestration
```

---

## Canonical Contracts (`contracts/`)

- [`contracts/agent_contract.md`](contracts/agent_contract.md): Agent invocation lifecycle (`AgentContext`, `AgentRequest`, `AgentResult`, `AgentAction`, `AgentStatus`).
- [`contracts/tool_contract.md`](contracts/tool_contract.md): Platform Tool Registry specifications, permission checks, schemas, and audit logging.
- [`contracts/event_contract.md`](contracts/event_contract.md): 16 canonical lifecycle events from `PR_OPENED` to `RECOVERY_COMPLETED`.
- [`contracts/deployment_contract.md`](contracts/deployment_contract.md): `DeploymentProvider` protocol and 10 canonical deployment states.
- [`contracts/memory_contract.md`](contracts/memory_contract.md): Ephemeral short-term, conversation, and project persistent memory tiers.
- [`contracts/review_contract.md`](contracts/review_contract.md): Structured AI code review schemas, finding taxonomies, and severity risk gates.

---

## Development Roadmap (`docs/development-workflow.md`)

- **Phase 0:** Foundation & Architecture Setup *(Complete)*
- **Phase 1:** Database Architecture & Data Pipelines *(Complete)*
- **Phase 2:** GitHub Integration *(Designed)*
- **Phase 3:** Context Engine *(Designed)*
- **Phase 4:** Tool Execution Boundary *(Designed)*
- **Phase 5:** Agent Runtime Loop *(Designed)*
- **Phase 6:** Review + Testing Engines *(Designed)*
- **Phase 7:** Risk Assessment & Guardrails *(Designed)*
- **Phase 8:** Deployment Adapters (Vercel, Render, Nebius) *(Designed)*
- **Phase 9:** Health Monitoring & Probes *(Designed)*
- **Phase 10:** Incident Recovery & Rollbacks *(Designed)*
- **Phase 11:** Semantic Memory (`pgvector`) & Evals *(Designed)*
- **Phase 12:** Nebius AI Cloud & Nemotron Model Routing *(Designed)*
- **Phase 13:** React Frontend Console *(Designed)*
- **Phase 14:** E2E Golden Path Testing & Demo *(Designed)*

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local test execution)
- Node.js 20+ (for frontend development)

### Quick Start with Docker Compose
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and launch services (PostgreSQL, FastAPI Backend, React Frontend)
docker compose up -d

# 3. Verify backend health
curl http://localhost:8000/health
```

### Local Backend Verification & Migrations
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run Alembic migrations against target database
cd backend
alembic upgrade head
cd ..

# Run automated tests (boundaries, contracts, database models, API flows, Alembic migration)
pytest backend/tests

# Run contract verification script
python scripts/verify_contracts.py
```
