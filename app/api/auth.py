"""
Authentication router — issues and refreshes JWT tokens.
"""

from fastapi import APIRouter, Request
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import issue_token
from app.models.schemas import TokenRequest, TokenResponse

router = APIRouter()


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Issue an API token",
    description=(
        "Pass any alphanumeric `user_id` to receive a signed JWT. "
        "No password required — designed for frictionless API exploration."
    ),
)
@limiter.limit(settings.rate_limit_auth)
async def get_token(body: TokenRequest, request: Request) -> TokenResponse:
    token = issue_token(body.user_id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expiry_minutes * 60,
    )
