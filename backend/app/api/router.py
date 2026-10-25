"""API V1 Router aggregating all domain sub-routers."""
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.github import router as github_router
from app.api.v1.events import router as events_router
from app.api.v1.agent import router as agent_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.tests import router as tests_router
from app.api.v1.gates import router as gates_router
from app.api.v1.deployments import router as deployments_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.memory import router as memory_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects_router, prefix="/projects", tags=["Projects"])

# Primary project-scoped routes
api_router.include_router(github_router, prefix="", tags=["GitHub"])
api_router.include_router(events_router, prefix="", tags=["Events"])
api_router.include_router(agent_router, prefix="", tags=["Agent"])
api_router.include_router(reviews_router, prefix="", tags=["Reviews"])
api_router.include_router(tests_router, prefix="", tags=["Tests"])
api_router.include_router(gates_router, prefix="", tags=["Deployment Gates"])
api_router.include_router(deployments_router, prefix="", tags=["Deployments"])
api_router.include_router(monitoring_router, prefix="", tags=["Monitoring"])
api_router.include_router(incidents_router, prefix="", tags=["Incidents"])
api_router.include_router(memory_router, prefix="", tags=["Memory"])

# Prefixed sub-routers
api_router.include_router(github_router, prefix="/github", tags=["GitHub"])
api_router.include_router(events_router, prefix="/events", tags=["Events"])
api_router.include_router(agent_router, prefix="/agent", tags=["Agent"])
api_router.include_router(reviews_router, prefix="/reviews", tags=["Reviews"])
api_router.include_router(tests_router, prefix="/tests", tags=["Tests"])
api_router.include_router(gates_router, prefix="/gates", tags=["Deployment Gates"])
api_router.include_router(deployments_router, prefix="/deployments", tags=["Deployments"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(incidents_router, prefix="/incidents", tags=["Incidents"])
api_router.include_router(memory_router, prefix="/memory", tags=["Memory"])
