from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

from nivesh.providers.openbb_gateway import OpenBBGateway


@pytest.mark.live
def test_live_reliance_price_returns_data_or_diagnostics() -> None:
    if os.getenv("RUN_LIVE_OPENBB") != "1":
        pytest.skip("Set RUN_LIVE_OPENBB=1 for the bounded provider smoke test")

    result = OpenBBGateway.from_openbb(provider="yfinance").fetch_prices(
        "RELIANCE.NS", start_date=date.today() - timedelta(days=10)
    )

    assert result.provider == "yfinance"
    assert result.data or result.warnings
