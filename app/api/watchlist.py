"""
Watchlist router — lets users save and manage tracked sectors.
New feature: not present in original project.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.core.rate_limit import limiter
from app.core.security import require_user
from app.core.config import settings
from app.models.schemas import WatchlistAddRequest, WatchlistEntry
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter()
_session = SessionService()


@router.get(
    "/watchlist",
    response_model=list[WatchlistEntry],
    summary="Get your watchlist",
)
@limiter.limit(settings.rate_limit_watchlist)
async def get_watchlist(request: Request, user_id: str = Depends(require_user)):
    return await _session.get_watchlist(user_id)


@router.post(
    "/watchlist",
    response_model=WatchlistEntry,
    status_code=status.HTTP_201_CREATED,
    summary="Add a sector to your watchlist",
)
@limiter.limit(settings.rate_limit_watchlist)
async def add_to_watchlist(
    body: WatchlistAddRequest,
    request: Request,
    user_id: str = Depends(require_user),
):
    watchlist = await _session.get_watchlist(user_id)
    if len(watchlist) >= 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Watchlist limit reached (20 sectors). Remove one before adding.",
        )
    return await _session.add_to_watchlist(user_id, body)


@router.delete(
    "/watchlist/{sector}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a sector from your watchlist",
)
@limiter.limit(settings.rate_limit_watchlist)
async def remove_from_watchlist(
    sector: str,
    request: Request,
    user_id: str = Depends(require_user),
):
    removed = await _session.remove_from_watchlist(user_id, sector)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sector '{sector}' not found in your watchlist.",
        )
