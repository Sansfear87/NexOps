# AI DevOps Assistant

[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-blue.svg)](docs/architecture.md)
[![Status](https://img.shields.io/badge/Phase-Phase%200%20Foundation-green.svg)](docs/development-workflow.md)
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

---

## Repository Structure

```
ai-devops-assistant/
├── frontend/             # React + TypeScript SPA developer dashboard
├── backend/              # FastAPI modular monolith (API, services, DB models)
├── agent/                # Isolated agent runtime interfaces and mock agent
├── contracts/            # Canonical contracts (agent, tool, event, deployment, memory, review)
├── docs/                 # Architectural blueprints and 15-phase implementation roadmap
├── scripts/              # Verification and developer utility scripts
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
- **Phase 1:** Authentication + Projects
- **Phase 2:** GitHub Integration
- **Phase 3:** Context Engine
- **Phase 4:** Tool Execution Boundary
- **Phase 5:** Agent Runtime Loop
- **Phase 6:** Review + Testing Engines
- **Phase 7:** Risk Assessment & Guardrails
- **Phase 8:** Deployment Adapters (Vercel & Render)
- **Phase 9:** Health Monitoring & Probes
- **Phase 10:** Incident Recovery & Rollbacks
- **Phase 11:** Semantic Memory (`pgvector`) & Evals
- **Phase 12:** Nebius AI Cloud & Nemotron Model Routing
- **Phase 13:** React Frontend Console
- **Phase 14:** E2E Golden Path Testing & Demo

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

### Local Backend Verification (without Docker)
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run automated tests
pytest backend/tests

# Run contract verification script
python scripts/verify_contracts.py
```
