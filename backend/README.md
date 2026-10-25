# Backend Modular Monolith

**Framework:** Python 3.11+ / FastAPI / SQLAlchemy / Alembic  
**Status:** Phases 0–14 Complete (All Phases Implemented, Tested & Verified)  
**Tests:** 72 Passing (100% test pass rate)

## Structure
- `app/api/v1/`: FastAPI route controllers (`auth`, `projects`, `github`, `events`, `agent`, `reviews`, `tests`, `gates`, `deployments`, `monitoring`, `incidents`, `memory`, `health`)
- `app/core/`: Configuration, security (`JWT`, `bcrypt`, AES Fernet encryption)
- `app/db/`: SQLAlchemy declarative base, models (`User`, `Project`, `APIKey`, `GitHubConnection`, `PullRequest`, `WebhookEvent`, `PlatformEvent`, `Review`, `ReviewFinding`, `TestRun`, `TestResult`, `DeploymentGate`, `GateAuditLog`, `Deployment`, `DeploymentLog`, `HealthCheck`, `HealthMetric`, `Incident`, `DiagnosisRun`, `ProjectMemoryItem`), repositories, and enums
- `app/schemas/`: Pydantic data schemas (`auth`, `project`, `event`, `review`, `test_run`, `deployment_gate`, `deployment`, `monitoring`, `incident`, `memory`)
- `app/services/`: Domain services (`AuthService`, `ProjectService`, `GitHubService`, `EventBus`, `DiffParser`, `ContextEngine`, `ToolExecutionService`, `AgentExecutionService`, `ReviewService`, `TestService`, `RiskService`, `DeploymentService`, `MonitoringService`, `IncidentService`, `MemoryService`, `ModelRouter`)
- `app/tools/`: Platform Tool Registry & Permission Guard (`deployment_tools`, `github_tools`, `test_tools`, etc.)
- `app/providers/`: Multi-cloud deployment adapters (`VercelAdapter`, `RenderAdapter`, `NebiusAdapter`)
- `alembic/`: Database migrations (001 through 006_phases_8_to_11_devops_loop)
- `tests/`: 72 automated pytest tests (boundaries, contracts, eval, API, DB, RBAC, migrations, tools, agent, reviews, tests, gates, deployments, monitoring, incidents, memory, model router, and e2e golden path loop)

## Running Tests Locally
```bash
pytest backend/tests -v
```
