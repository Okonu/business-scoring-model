"""Service routes"""

from fastapi import APIRouter

from health_score import __version__
from health_score.api import schemas
from health_score.scoring import ENGINE_VERSION

router = APIRouter(tags=["system"])


@router.get("/health", response_model=schemas.Health, summary="Liveness check")
async def health():
    return {"status": "ok", "version": __version__, "engine_version": ENGINE_VERSION}
