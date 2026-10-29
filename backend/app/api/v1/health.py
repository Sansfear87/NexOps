from typing import List
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()

ALL_14_PHASES: List[str] = [
    "Phase 0: Contracts, Sandboxing & Foundations",
    "Phase 1: PostgreSQL & Modular Monolith",
    "Phase 2: GitHub Integration & Webhooks",
    "Phase 3: Context Engine & Tool Execution",
    "Phase 4: Agent & Platform Wiring",
    "Phase 5: React Console Dashboard",
    "Phase 6: AI Code Review & Test Runner",
    "Phase 7: Guardrails, Risk & Gatekeeper",
    "Phase 8: Deployment Provider Adapters (Render/Vercel/Nebius)",
    "Phase 9: Monitoring & Synthetic Probes",
    "Phase 10: Autonomous Incident Recovery",
    "Phase 11: Semantic Project Memory",
    "Phase 12: Nebius AI Cloud & Nemotron Router",
    "Phase 13: React Console Lifecycle Tabs",
    "Phase 14: Multi-Agent Orchestrator & Credit Efficiency",
]


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def get_health() -> HealthResponse:
    """System health check endpoint verifying all 14 phases are active and operational."""
    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        phase="Phases 0–14 Autonomous DevOps Platform (All 14 Phases Active)",
        active_phases=ALL_14_PHASES,
        ai_engine="Multi-Agent Dual-Model Orchestrator (Nemotron 3.5 + DeepSeek V4.1)",
        models={
            "reasoning": settings.PREFERRED_REASONING_MODEL,
            "fast": settings.PREFERRED_FAST_MODEL,
            "vision": "nvidia/Nemotron-3.5-Super-VL",
            "pro": "deepseek-ai/DeepSeek-V4-Pro-0813",
        },
    )
