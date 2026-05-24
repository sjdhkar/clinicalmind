"""Health endpoint for ai-orchestrator."""

import time
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])
_start = time.time()


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    service: str


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        uptime_seconds=round(time.time() - _start, 1),
        service="clinicalmind-ai-orchestrator",
    )
