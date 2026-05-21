"""
History router — query history per user.
"""

from fastapi import APIRouter, Depends, Request
from app.core.rate_limit import limiter
from app.core.security import require_user
from app.models.schemas import HistoryResponse
from app.services.session_service import SessionService

router = APIRouter()
_session = SessionService()


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Get your query history",
    description="Returns the last 50 market intelligence queries for the authenticated user.",
)
@limiter.limit("30/minute")
async def get_history(request: Request, user_id: str = Depends(require_user)):
    records = await _session.get_history(user_id)
    return HistoryResponse(
        user_id=user_id,
        total_queries=len(records),
        records=records,
    )


@router.delete(
    "/history",
    status_code=204,
    summary="Clear your query history",
)
@limiter.limit("10/minute")
async def clear_history(request: Request, user_id: str = Depends(require_user)):
    await _session.clear_history(user_id)
