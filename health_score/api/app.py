"""
FastAPI application

Run:
    uvicorn health_score.api.app:app --port 8100
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from health_score import __version__
from health_score.api.routes import scores, system
from health_score.basepoint import AuthenticationError, BasepointUnavailableError
from health_score.logging_config import configure_logging
from health_score.service import ScoringService
from health_score.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, service: ScoringService | None = None) -> FastAPI:
    """
    Build the application

    Args:
        settings: defaults to settings from the environment
        service: inject a service (tests); defaults to one built from settings
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Business Health Score API",
        description="Scores a BASEPOINT business from all the data its products hold.",
        version=__version__,
    )
    app.state.settings = settings
    app.state.service = service or ScoringService(settings)
    app.include_router(system.router)
    app.include_router(scores.router)

    @app.exception_handler(AuthenticationError)
    async def _auth_error(_: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(BasepointUnavailableError)
    async def _unavailable(_: Request, exc: BasepointUnavailableError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        logger.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal error"})

    return app


app = create_app()
