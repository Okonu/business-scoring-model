"""Scoring routes (v1)"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from health_score.api import schemas
from health_score.api.dependencies import get_service, require_api_key
from health_score.service import Credentials, ScoringService

router = APIRouter(prefix="/v1", tags=["scores"], dependencies=[Depends(require_api_key)])


@router.post("/scores", response_model=schemas.ScoreResponse, summary="Score a business")
async def create_score(body: schemas.ScoreRequest, service: Annotated[ScoringService, Depends(get_service)]):
    """
    Log in to BASEPOINT as the business, collect its data and return its
    health score with the full breakdown: the same data the web page shows.
    """
    credentials = Credentials(body.company_code, body.pin.get_secret_value(), body.username)
    return await run_in_threadpool(service.score, credentials, body.as_of_date)
