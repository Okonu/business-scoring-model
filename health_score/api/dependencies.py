"""FastAPI dependencies: settings, service and API-key check"""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from health_score.service import ScoringService
from health_score.settings import Settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_service(request: Request) -> ScoringService:
    return request.app.state.service


def require_api_key(
    key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Enforced only when API_KEYS is set"""
    allowed = settings.api_key_list
    if not allowed:
        return
    if not key or not any(secrets.compare_digest(key, k) for k in allowed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
