"""Bounded dataset caches, targeted refresh keys, and secret application."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

import streamlit as st

from nivesh.domain.models import (
    AnalysisBundle,
    CompanyProfile,
    DatasetResult,
    PricePoint,
    ProviderBundle,
    StatementDatasets,
)
from nivesh.providers.openbb_gateway import OpenBBGateway, set_runtime_credentials
from nivesh.services.analysis import assemble_provider_bundle

_SUPPORTED_CREDENTIALS = (
    "benzinga_api_key",
    "econdb_api_key",
    "fmp_api_key",
    "fred_api_key",
    "intrinio_api_key",
    "tiingo_token",
    "tradingeconomics_api_key",
)


@st.cache_resource(max_entries=8, show_spinner=False)
def get_gateway(provider: str) -> OpenBBGateway:
    """Reuse one OpenBB client adapter per configured provider."""

    return OpenBBGateway.from_openbb(provider=provider)


@st.cache_data(ttl=21_600, max_entries=128, show_spinner=False)
def load_profile(
    symbol: str, provider: str, refresh_nonce: int
) -> DatasetResult[CompanyProfile]:
    """Load a company profile with a six-hour bounded cache."""

    return get_gateway(provider).fetch_profile(symbol)


@st.cache_data(ttl=900, max_entries=128, show_spinner=False)
def load_prices(
    symbol: str, provider: str, refresh_nonce: int
) -> DatasetResult[list[PricePoint]]:
    """Load five years of prices with a 15-minute bounded cache."""

    start_date = date.today() - timedelta(days=365 * 5)
    return get_gateway(provider).fetch_prices(symbol, start_date=start_date)


@st.cache_data(ttl=86_400, max_entries=256, show_spinner=False)
def load_statements(
    symbol: str,
    provider: str,
    period: str,
    refresh_nonce: int,
) -> StatementDatasets:
    """Load reported statements with a daily bounded cache."""

    return get_gateway(provider).fetch_statements(symbol, period)


@st.cache_data(ttl=21_600, max_entries=256, show_spinner=False)
def load_metrics(
    symbol: str,
    provider: str,
    period: str,
    refresh_nonce: int,
) -> DatasetResult[dict[str, float | None]]:
    """Load provider valuation metrics with a six-hour bounded cache."""

    return get_gateway(provider).fetch_metrics(symbol, period)


def load_analysis(
    symbol: str,
    provider: str,
    period: str,
    refresh_nonce: int,
) -> AnalysisBundle:
    """Assemble independently cached datasets without masking partial failures."""

    provider_bundle = ProviderBundle(
        symbol=symbol,
        profile=load_profile(symbol, provider, refresh_nonce),
        prices=load_prices(symbol, provider, refresh_nonce),
        statements=load_statements(symbol, provider, period, refresh_nonce),
        metrics=load_metrics(symbol, provider, period, refresh_nonce),
    )
    return assemble_provider_bundle(provider_bundle, period)


def bump_refresh_nonce(
    current: Mapping[str, int], symbol: str, provider: str
) -> dict[str, int]:
    """Increment only the active provider/symbol cache key."""

    key = f"{provider}:{symbol}"
    updated = dict(current)
    updated[key] = updated.get(key, 0) + 1
    return updated


def configure_openbb_credentials(
    secrets: Mapping[str, Any],
    *,
    credentials: Any | None = None,
) -> tuple[str, ...]:
    """Apply allow-listed non-empty provider keys server-side without logging values."""

    applied: list[str] = []
    runtime_values: dict[str, str] = {}
    for key in _SUPPORTED_CREDENTIALS:
        value = secrets.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        if credentials is None:
            runtime_values[key] = value.strip()
        elif hasattr(credentials, key):
            setattr(credentials, key, value.strip())
        else:
            continue
        applied.append(key)
    if runtime_values:
        set_runtime_credentials(runtime_values)
    return tuple(applied)
