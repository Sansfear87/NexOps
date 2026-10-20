# Backend Modular Monolith

**Framework:** Python 3.11+ / FastAPI / SQLAlchemy / Alembic  
**Status:** Phases 1–5 Complete (Auth, RBAC, GitHub, Context Engine, Tool Gatekeeper, Agent Wiring)  
**Tests:** 43 Passing (100% test pass rate)

## Structure
- `app/api/v1/`: FastAPI route controllers (`auth`, `projects`, `github`, `events`, `agent`, `health`)
- `app/core/`: Configuration, security (`JWT`, `bcrypt`, AES Fernet encryption)
- `app/db/`: SQLAlchemy declarative base, models (`User`, `Project`, `APIKey`, `GitHubConnection`, `PullRequest`, `WebhookEvent`, `PlatformEvent`), repositories, and enums
- `app/schemas/`: Pydantic data schemas
- `app/services/`: Domain services (`AuthService`, `ProjectService`, `GitHubService`, `EventBus`, `DiffParser`, `ContextEngine`, `ToolExecutionService`, `AgentExecutionService`)
- `app/tools/`: Platform Tool Registry & Permission Guard
- `app/providers/`: Deployment provider interface (`DeploymentProvider`) and adapters
- `alembic/`: Database migrations (001_phase1_auth_and_projects, 002_phase1_api_keys, 003_phase2_github_and_events)
- `tests/`: 43 automated pytest tests (boundaries, contracts, eval, API, DB, RBAC, migrations, tools, agent)

## Running Tests Locally
```bash
pytest backend/tests -v
```
