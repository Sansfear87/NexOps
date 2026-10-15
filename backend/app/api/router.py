"""API V1 Router aggregating all domain sub-routers."""
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.github import router as github_router
from app.api.v1.events import router as events_router
from app.api.v1.agent import router as agent_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects_router, prefix="/projects", tags=["Projects"])

# Primary project-scoped routes (/projects/{id}/github, /projects/{id}/events, /projects/{id}/agent, /webhooks/github/{id})
api_router.include_router(github_router, prefix="", tags=["GitHub"])
api_router.include_router(events_router, prefix="", tags=["Events"])
api_router.include_router(agent_router, prefix="", tags=["Agent"])

# Prefixed sub-routers (/github, /events, /agent)
api_router.include_router(github_router, prefix="/github", tags=["GitHub"])
api_router.include_router(events_router, prefix="/events", tags=["Events"])
api_router.include_router(agent_router, prefix="/agent", tags=["Agent"])
