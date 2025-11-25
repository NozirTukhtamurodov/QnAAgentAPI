"""Health check and monitoring endpoints."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, status

from domain.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API is running and healthy",
)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring and load balancers."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
)
async def readiness_check() -> dict[str, str]:
    """Readiness check for Kubernetes probes."""
    return {"status": "ready"}


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
)
async def liveness_check() -> dict[str, str]:
    """Liveness check for Kubernetes probes."""
    return {"status": "alive"}
