"""
Market Insights router — the core intelligence endpoint.

POST /v2/insights → AI-generated, scored market opportunity report.
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import require_user
from app.models.schemas import InsightRequest, InsightResponse, SectorScore
from app.services.search_service import MarketSearchService
from app.services.intelligence_service import IntelligenceService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter()

_searcher = MarketSearchService()
_ai = IntelligenceService()
_session = SessionService()


@router.post(
    "/insights",
    response_model=InsightResponse,
    summary="Generate a market intelligence report",
    description=(
        "Fetches live market data from the web and synthesises it into a structured "
        "trade intelligence report using Gemini AI. Reports are scored 0-100 across "
        "four dimensions: market size, growth velocity, competitive gap, and risk."
    ),
    responses={
        429: {"description": "Rate limit exceeded — slow down."},
        503: {"description": "AI service temporarily unavailable."},
    },
)
@limiter.limit(settings.rate_limit_insights)
async def generate_insight(
    body: InsightRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> InsightResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    region = body.region or "Global"

    logger.info(
        "insight | user=%s | sector=%s | region=%s | depth=%s | req=%s",
        user_id, body.sector, region, body.depth, request_id,
    )

    start_ms = time.monotonic()

    # ── 1. Record query start ────────────────────────────────────────────────
    await _session.record_query(user_id, body.sector, region, body.depth, "in_progress")

    # ── 2. Fetch live market data ────────────────────────────────────────────
    raw_data = await _searcher.fetch(body.sector, region)

    # ── 3. Run AI analysis ───────────────────────────────────────────────────
    try:
        analysis = await _ai.analyse(
            sector=body.sector,
            region=region,
            depth=body.depth,
            market_data=raw_data,
        )
    except HTTPException:
        await _session.record_query(user_id, body.sector, region, body.depth, "failed")
        raise

    elapsed_ms = int((time.monotonic() - start_ms) * 1000)

    # ── 4. Extract structured score from analysis ────────────────────────────
    score = _ai.extract_score(analysis)

    # ── 5. Record success ────────────────────────────────────────────────────
    await _session.record_query(
        user_id, body.sector, region, body.depth, "completed",
        processing_ms=elapsed_ms,
    )

    logger.info(
        "insight done | user=%s | sector=%s | %dms | req=%s",
        user_id, body.sector, elapsed_ms, request_id,
    )

    return InsightResponse(
        request_id=request_id,
        sector=body.sector,
        region=region,
        depth=body.depth,
        generated_at=datetime.now(timezone.utc),
        processing_ms=elapsed_ms,
        report_markdown=analysis,
        score=score,
    )


@router.get(
    "/insights/sectors",
    summary="List popular sectors",
    description="Returns a curated list of sectors users commonly query.",
)
async def popular_sectors():
    return {
        "sectors": [
            "Pharmaceuticals", "Green Hydrogen", "Electric Vehicles",
            "Semiconductors", "Aerospace & Defence", "Textiles & Apparel",
            "Specialty Chemicals", "Agri-Tech", "Medical Devices",
            "Renewable Energy", "IT Services", "Logistics & Freight",
        ]
    }
