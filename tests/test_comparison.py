"""Comparison alignment, limits, and browser-payload safety contracts."""

from __future__ import annotations

import math

import pytest

from nivesh.domain.models import AnalysisBundle
from nivesh.services.analysis import load_demo_analysis
from nivesh.services.comparison import build_comparison, normalized_price_frame


@pytest.fixture
def bundles() -> list[AnalysisBundle]:
    return [
        load_demo_analysis("RELIANCE.NS", "annual"),
        load_demo_analysis("TCS.NS", "annual"),
    ]


def test_prices_normalize_each_company_to_100(bundles: list[AnalysisBundle]) -> None:
    frame = normalized_price_frame(bundles)
    first_valid = frame.apply(lambda column: column.dropna().iloc[0])

    assert first_valid.to_dict() == {"RELIANCE.NS": 100.0, "TCS.NS": 100.0}


@pytest.mark.parametrize("count", [0, 1, 5])
def test_comparison_requires_two_to_four_companies(
    bundles: list[AnalysisBundle], count: int
) -> None:
    repeated = [bundles[index % len(bundles)] for index in range(count)]

    with pytest.raises(ValueError, match="two to four"):
        build_comparison(repeated)


def test_comparison_rejects_duplicate_symbols(bundles: list[AnalysisBundle]) -> None:
    with pytest.raises(ValueError, match="unique"):
        build_comparison([bundles[0], bundles[0]])


def test_payload_keeps_exact_values_and_provenance(
    bundles: list[AnalysisBundle],
) -> None:
    payload = build_comparison(bundles)

    reliance_revenue = next(
        row
        for row in payload.rows
        if row.symbol == "RELIANCE.NS" and row.metric == "revenue"
    )
    assert reliance_revenue.value == 10_942_500_000_000
    assert reliance_revenue.period == "FY 2026"
    assert reliance_revenue.currency == "INR"
    assert reliance_revenue.provider == "demo"


def test_tower_payload_contains_only_finite_numbers_or_none(
    bundles: list[AnalysisBundle],
) -> None:
    payload = build_comparison(bundles)

    assert len(payload.towers) == 2
    for company in payload.towers:
        assert len(company.symbol) <= 24
        assert all(value is None or math.isfinite(value) for value in company.values.values())
        table_scores = {
            row.metric: row.value
            for row in payload.rows
            if row.symbol == company.symbol
            and row.metric
            in {"composite", "quality", "growth", "balance_sheet", "valuation"}
        }
        assert table_scores == company.values
