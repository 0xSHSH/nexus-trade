"""
Core application configuration.
All settings are loaded from environment variables / .env file.
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ── Identity ──────────────────────────────────────────────────────────────
    app_name: str = "NexusTrade"
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # ── AI ────────────────────────────────────────────────────────────────────
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model: str = Field(
        default="gemini-2.0-flash-lite",
        alias="GEMINI_MODEL",
    )
    gemini_max_output_tokens: int = Field(default=3072, alias="GEMINI_MAX_TOKENS")
    gemini_temperature: float = Field(default=0.25, alias="GEMINI_TEMPERATURE")

    # ── Security ──────────────────────────────────────────────────────────────
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = Field(default=120, alias="JWT_EXPIRY_MINUTES")

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="ALLOWED_ORIGINS",
    )

    # ── Rate limits ───────────────────────────────────────────────────────────
    rate_limit_insights: str = Field(default="8/minute",  alias="RATE_LIMIT_INSIGHTS")
    rate_limit_auth: str     = Field(default="20/minute", alias="RATE_LIMIT_AUTH")
    rate_limit_watchlist: str = Field(default="30/minute", alias="RATE_LIMIT_WATCHLIST")

    # ── Search ────────────────────────────────────────────────────────────────
    search_max_results: int = Field(default=6, alias="SEARCH_MAX_RESULTS")
    search_context_chars: int = Field(default=18000, alias="SEARCH_CONTEXT_CHARS")

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        populate_by_name = True


settings = Settings()
