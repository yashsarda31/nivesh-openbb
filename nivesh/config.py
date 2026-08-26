"""Application configuration with safe production defaults."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    """Validated settings shared by providers and the Streamlit interface."""

    model_config = ConfigDict(frozen=True)

    provider: str = "yfinance"
    demo_mode: bool = False
    price_ttl_seconds: int = Field(default=900, ge=0)
    profile_ttl_seconds: int = Field(default=21_600, ge=0)
    statement_ttl_seconds: int = Field(default=86_400, ge=0)
    request_timeout_seconds: int = Field(default=30, ge=1, le=120)
    max_retries: int = Field(default=1, ge=0, le=3)
    retry_backoff_seconds: float = Field(default=1.5, ge=0.0)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> AppSettings:
        """Build settings from a mapping such as environment variables or secrets."""

        return cls(
            provider=str(mapping.get("NIVESH_PROVIDER", "yfinance")),
            demo_mode=str(mapping.get("NIVESH_DEMO_MODE", "false")).lower()
            in {"1", "true", "yes", "on"},
            price_ttl_seconds=int(mapping.get("NIVESH_PRICE_TTL", 900)),
            profile_ttl_seconds=int(mapping.get("NIVESH_PROFILE_TTL", 21_600)),
            statement_ttl_seconds=int(mapping.get("NIVESH_STATEMENT_TTL", 86_400)),
            request_timeout_seconds=int(mapping.get("NIVESH_REQUEST_TIMEOUT", 30)),
            max_retries=int(mapping.get("NIVESH_MAX_RETRIES", 1)),
            retry_backoff_seconds=float(mapping.get("NIVESH_RETRY_BACKOFF", 1.5)),
        )
