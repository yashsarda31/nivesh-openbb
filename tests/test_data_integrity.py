"""Regressions for source dates and comparable research views."""

from datetime import date

import pytest

from nivesh.domain.models import AnalysisBundle, PricePoint
from nivesh.providers.openbb_gateway import OpenBBGateway
from nivesh.services.analysis import assemble_provider_bundle, load_demo_analysis
from nivesh.services.comparison import build_comparison, normalized_price_frame
from tests.fixtures.openbb_payloads import FakeOBB


def test_profile_does_not_invent_source_date_from_fetch_time() -> None:
    result = OpenBBGateway(FakeOBB()).fetch_profile("RELIANCE.NS")
    assert result.as_of is None


def test_latest_metrics_record_is_selected_regardless_of_provider_order() -> None:
    client = FakeOBB()
    client.payloads["metrics"] = [
        {"period_ending": "2026-03-31", "pe_ratio": 20.0},
        {"period_ending": "2025-03-31", "pe_ratio": 30.0},
    ]
    result = OpenBBGateway(client).fetch_metrics("RELIANCE.NS", "annual")
    assert result.data["pe_ratio"] == 20.0
    assert result.as_of == date(2026, 3, 31)


def test_yfinance_percentage_debt_equity_is_normalized_once() -> None:
    client = FakeOBB()
    client.payloads["metrics"] = [{"debt_to_equity": 25.0, "enterprise_to_ebitda": 12.0}]
    metrics = OpenBBGateway(client, provider="yfinance").fetch_metrics("TCS.NS", "annual")
    assert metrics.data["debt_equity"] == 0.25


def test_comparison_uses_shared_valuation_aliases() -> None:
    one = load_demo_analysis("RELIANCE.NS", "annual")
    metrics = one.metrics.model_copy(update={"data": {"enterprise_to_ebitda": 12.0}})
    one = one.model_copy(update={"metrics": metrics})
    payload = build_comparison([one, load_demo_analysis("TCS.NS", "annual")])
    ev = next(
        row for row in payload.rows if row.symbol == one.symbol and row.metric == "ev_to_ebitda"
    )
    assert ev.value == 12.0


def test_old_statement_source_date_is_marked_stale() -> None:
    raw = OpenBBGateway(FakeOBB()).fetch_provider_bundle("RELIANCE.NS", "quarterly")
    bundle = assemble_provider_bundle(raw, "quarterly")
    assert bundle.statements.stale


def test_comparison_rejects_mixed_reporting_frequencies() -> None:
    bundles = [
        load_demo_analysis("RELIANCE.NS", "annual"),
        load_demo_analysis("TCS.NS", "quarterly"),
    ]
    with pytest.raises(ValueError, match="same reporting frequency"):
        build_comparison(bundles)


def _with_prices(bundle: AnalysisBundle, values: list[tuple[date, float]]) -> AnalysisBundle:
    prices = [PricePoint(date=day, close=close) for day, close in values]
    return bundle.model_copy(update={"prices": bundle.prices.model_copy(update={"data": prices})})


def test_price_comparison_uses_first_shared_positive_close() -> None:
    one = _with_prices(
        load_demo_analysis("RELIANCE.NS", "annual"),
        [
            (date(2026, 1, 1), 50),
            (date(2026, 1, 2), 100),
            (date(2026, 1, 3), 110),
        ],
    )
    two = _with_prices(
        load_demo_analysis("TCS.NS", "annual"),
        [
            (date(2026, 1, 2), 200),
            (date(2026, 1, 3), 220),
        ],
    )
    frame = normalized_price_frame([one, two])
    assert frame.index[0].date() == date(2026, 1, 2)
    assert frame.iloc[0].to_dict() == {"RELIANCE.NS": 100.0, "TCS.NS": 100.0}
    assert frame.iloc[-1].to_dict() == pytest.approx({"RELIANCE.NS": 110.0, "TCS.NS": 110.0})


def test_price_comparison_does_not_invent_overlap() -> None:
    one = _with_prices(load_demo_analysis("RELIANCE.NS", "annual"), [(date(2026, 1, 1), 10)])
    two = _with_prices(load_demo_analysis("TCS.NS", "annual"), [(date(2026, 1, 2), 20)])
    assert normalized_price_frame([one, two]).empty
