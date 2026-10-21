# Backend Modular Monolith

**Framework:** Python 3.11+ / FastAPI / SQLAlchemy / Alembic  
**Status:** Phases 1–6 Complete (Auth, RBAC, GitHub, Context Engine, Tool Gatekeeper, Agent Wiring, AI Review Engine, Test Runner)  
**Tests:** 51 Passing (100% test pass rate)

## Structure
- `app/api/v1/`: FastAPI route controllers (`auth`, `projects`, `github`, `events`, `agent`, `reviews`, `tests`, `health`)
- `app/core/`: Configuration, security (`JWT`, `bcrypt`, AES Fernet encryption)
- `app/db/`: SQLAlchemy declarative base, models (`User`, `Project`, `APIKey`, `GitHubConnection`, `PullRequest`, `WebhookEvent`, `PlatformEvent`, `Review`, `ReviewFinding`, `TestRun`, `TestResult`), repositories, and enums
- `app/schemas/`: Pydantic data schemas (`auth`, `project`, `event`, `review`, `test_run`)
- `app/services/`: Domain services (`AuthService`, `ProjectService`, `GitHubService`, `EventBus`, `DiffParser`, `ContextEngine`, `ToolExecutionService`, `AgentExecutionService`, `ReviewService`, `TestService`)
- `app/tools/`: Platform Tool Registry & Permission Guard
- `app/providers/`: Deployment provider interface (`DeploymentProvider`) and adapters
- `alembic/`: Database migrations (001, 002, 003, 004_phase6_reviews_and_testing)
- `tests/`: 51 automated pytest tests (boundaries, contracts, eval, API, DB, RBAC, migrations, tools, agent, reviews, tests)

## Running Tests Locally
```bash
pytest backend/tests -v
```
