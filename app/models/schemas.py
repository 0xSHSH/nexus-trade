"""
Pydantic schemas — the single source of truth for all request/response shapes.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
import re


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    """Request body for issuing a JWT."""
    user_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Unique alphanumeric identifier for the caller.",
        examples=["portfolio-demo-user"],
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", v):
            raise ValueError("user_id may only contain letters, numbers, hyphens and underscores.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds.")


# ── Market Insights ───────────────────────────────────────────────────────────

class InsightRequest(BaseModel):
    """Body for a POST /v2/insights request."""
    sector: str = Field(
        ...,
        min_length=2,
        max_length=80,
        description="Industry vertical to analyse (e.g. 'semiconductors', 'green hydrogen').",
        examples=["pharmaceuticals", "electric vehicles"],
    )
    region: Optional[str] = Field(
        default=None,
        max_length=60,
        description="Optional focus region (e.g. 'Southeast Asia', 'EU'). Defaults to global.",
        examples=["Southeast Asia", "Middle East"],
    )
    depth: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="Analysis depth: quick (summary), standard (full), deep (with risk matrix).",
    )

    @field_validator("sector", "region", mode="before")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Strip prompt-injection attempts; keep only safe chars
        cleaned = re.sub(r"[^\w\s\-,&()./']", "", v).strip()
        if len(cleaned) < 2:
            raise ValueError("Field contains too many special characters.")
        return cleaned


class SectorScore(BaseModel):
    """Composite opportunity score for a sector."""
    overall: int = Field(..., ge=0, le=100, description="0-100 composite score.")
    market_size: int = Field(..., ge=0, le=100)
    growth_velocity: int = Field(..., ge=0, le=100)
    competitive_gap: int = Field(..., ge=0, le=100)
    risk_adjusted: int = Field(..., ge=0, le=100)


class InsightResponse(BaseModel):
    """Full market intelligence response."""
    request_id: str
    sector: str
    region: str
    depth: str
    generated_at: datetime
    processing_ms: int
    report_markdown: str
    score: Optional[SectorScore] = None


# ── Watchlist ─────────────────────────────────────────────────────────────────

class WatchlistEntry(BaseModel):
    sector: str
    region: str
    added_at: datetime
    last_checked: Optional[datetime] = None
    alert_enabled: bool = False


class WatchlistAddRequest(BaseModel):
    sector: str = Field(..., min_length=2, max_length=80)
    region: str = Field(default="Global", max_length=60)
    alert_enabled: bool = False


# ── History ───────────────────────────────────────────────────────────────────

class HistoryRecord(BaseModel):
    sector: str
    region: str
    depth: str
    status: Literal["completed", "failed", "in_progress"]
    timestamp: datetime
    processing_ms: Optional[int] = None


class HistoryResponse(BaseModel):
    user_id: str
    total_queries: int
    records: List[HistoryRecord]


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None
