"""
NexusTrade — AI-Powered Global Market Intelligence Platform
Entry point for the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.middleware import SecurityHeadersMiddleware
from app.api.auth import router as auth_router
from app.api.insights import router as insights_router
from app.api.watchlist import router as watchlist_router
from app.api.history import router as history_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NexusTrade API starting up | env=%s", settings.environment)
    yield
    logger.info("NexusTrade API shutting down")


app = FastAPI(
    title="NexusTrade — Market Intelligence API",
    description=(
        "Real-time AI-powered trade intelligence for global markets. "
        "Identify opportunities, benchmark competitors, and surface risks — "
        "all in a single structured API call."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware stack (outermost first) ────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,     prefix="/v2", tags=["Authentication"])
app.include_router(insights_router, prefix="/v2", tags=["Market Insights"])
app.include_router(watchlist_router,prefix="/v2", tags=["Watchlist"])
app.include_router(history_router,  prefix="/v2", tags=["History"])


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness probe — returns system health and version info."""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "version": app.version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
