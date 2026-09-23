# Backend Modular Monolith

**Framework:** Python 3.11+ / FastAPI / SQLAlchemy / Alembic  
**Status:** Phase 0 Architecture Placeholder  

## Structure
- `app/api/`: FastAPI route controllers (`/health`, `/api/v1`)
- `app/core/`: Configuration and settings (`config.py`)
- `app/models/`: SQLAlchemy declarative base and ORM models
- `app/schemas/`: Pydantic data schemas
- `app/services/`: Modular monolith domain services (Auth, GitHub, Deployment, Incident)
- `app/tools/`: Platform Tool Registry & Permission Guard
- `app/providers/`: Deployment provider interface (`DeploymentProvider`) and adapters
- `tests/`: Automated pytest suite verifying health, contracts, and boundary isolation

## Running Tests Locally
```bash
pytest backend/tests
```
