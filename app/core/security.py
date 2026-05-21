"""
JWT-based stateless authentication.
Issues signed HS256 tokens; no database required for validation.
"""

from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=True)

_TOKEN_SUB_KEY = "sub"
_TOKEN_TYPE_KEY = "typ"
_TOKEN_TYPE_ACCESS = "access"


def issue_token(user_id: str) -> str:
    """Create a signed JWT for the given user_id."""
    now = datetime.now(timezone.utc)
    payload = {
        _TOKEN_SUB_KEY: user_id,
        _TOKEN_TYPE_KEY: _TOKEN_ACCESS,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


_TOKEN_ACCESS = _TOKEN_TYPE_ACCESS


def _decode(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired. Request a new one via POST /v2/auth/token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency — resolves to the authenticated user_id."""
    payload = _decode(credentials.credentials)
    user_id = payload.get(_TOKEN_SUB_KEY)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
        )
    return user_id


def peek_user_id(request: Request) -> str | None:
    """Non-raising helper — extracts user_id from header if present."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        payload = _decode(auth_header[7:])
        return payload.get(_TOKEN_SUB_KEY)
    except HTTPException:
        return None
