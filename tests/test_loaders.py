"""Dataset cache, targeted refresh, and credential-boundary contracts."""

from __future__ import annotations

import builtins
from collections import Counter
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from nivesh.domain.models import DatasetResult, PricePoint
from nivesh.services import loaders


class CountingGateway:
    def __init__(self) -> None:
        self.calls: Counter[str] = Counter()

    def fetch_prices(self, symbol: str, start_date: date) -> DatasetResult[list[PricePoint]]:
        self.calls[symbol] += 1
        return DatasetResult(
            data=[PricePoint(date=start_date, close=100.0)],
            provider="yfinance",
            retrieved_at=datetime.now(UTC),
            as_of=start_date,
        )


def test_credentials_do_not_import_generated_openbb_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def reject_generated_sdk(name, *args, **kwargs):
        if name == "openbb":
            raise PermissionError("read-only site-packages/openbb/.build.lock")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_generated_sdk)

    applied = loaders.configure_openbb_credentials({"fmp_api_key": "server-secret"})

    assert applied == ("fmp_api_key",)


def test_refresh_nonce_invalidates_only_selected_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = CountingGateway()
    monkeypatch.setattr(loaders, "get_gateway", lambda provider: gateway)
    loaders.load_prices.clear()

    loaders.load_prices("RELIANCE.NS", "yfinance", 0)
    loaders.load_prices("TCS.NS", "yfinance", 0)
    nonces = loaders.bump_refresh_nonce({}, "RELIANCE.NS", "yfinance")
    loaders.load_prices("RELIANCE.NS", "yfinance", nonces["yfinance:RELIANCE.NS"])
    loaders.load_prices("TCS.NS", "yfinance", 0)

    assert gateway.calls["RELIANCE.NS"] == 2
    assert gateway.calls["TCS.NS"] == 1


def test_refresh_nonce_preserves_other_entries() -> None:
    updated = loaders.bump_refresh_nonce(
        {"yfinance:TCS.NS": 3},
        "RELIANCE.NS",
        "yfinance",
    )

    assert updated == {"yfinance:TCS.NS": 3, "yfinance:RELIANCE.NS": 1}


def test_credentials_apply_only_allowlisted_non_empty_values() -> None:
    credentials = SimpleNamespace(fmp_api_key=None, intrinio_api_key=None)

    applied = loaders.configure_openbb_credentials(
        {
            "fmp_api_key": "server-secret",
            "intrinio_api_key": "",
            "unknown_key": "must-not-apply",
        },
        credentials=credentials,
    )

    assert applied == ("fmp_api_key",)
    assert credentials.fmp_api_key == "server-secret"
    assert credentials.intrinio_api_key is None
    assert not hasattr(credentials, "unknown_key")
