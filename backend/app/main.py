import sys
from pathlib import Path

# Ensure backend root and workspace root are in sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
_root_dir = _backend_dir.parent
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.api.v1.health import router as health_router
from app.core.config import settings


def create_application() -> FastAPI:
    """Application factory for the AI DevOps Assistant FastAPI service."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Persistent AI Developer Control Plane & Autonomous Deployment Orchestrator",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration - robust handling for credentials with regex fallback
    safe_origins = [o for o in settings.CORS_ORIGINS if o != "*"]
    if not safe_origins:
        safe_origins = [
            "https://nexops-frontend.onrender.com",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=safe_origins,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount health endpoint both at root /health and /api/v1
    application.include_router(health_router, prefix="", tags=["System"])
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()
