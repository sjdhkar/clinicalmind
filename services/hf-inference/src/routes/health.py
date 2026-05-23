"""Health check endpoint — used by Docker, K8s liveness/readiness probes."""

import time

from fastapi import APIRouter
from pydantic import BaseModel

from src.models.registry import get_loaded_models

router = APIRouter(prefix="/health", tags=["health"])

_start_time = time.time()


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    models_loaded: dict[str, bool]


@router.get("", response_model=HealthResponse, summary="Service health")
async def health() -> HealthResponse:
    """
    Returns service health and which models are currently in memory.

    - K8s liveness probe: check status == "ok"
    - K8s readiness probe: if preload_models=True, also check all models are loaded
    """
    loaded = get_loaded_models()
    return HealthResponse(
        status="ok",
        uptime_seconds=round(time.time() - _start_time, 1),
        models_loaded=loaded,
    )
