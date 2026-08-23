"""Exact-value and empty-state contracts for financial charts."""

from __future__ import annotations

from datetime import date

import pandas as pd

from nivesh.domain.models import FinancialPeriod, PricePoint
from nivesh.ui.charts import (
    comparison_figure,
    financial_trend_figure,
    margin_figure,
    price_figure,
)


def _periods() -> list[FinancialPeriod]:
    return [
        FinancialPeriod(
            period_ending=date(2024, 3, 31),
            revenue=800.0,
            net_income=80.0,
            metrics={"operating_margin": 0.12, "net_margin": 0.10},
        ),
        FinancialPeriod(
            period_ending=date(2025, 3, 31),
            revenue=1_000.0,
            net_income=110.0,
            metrics={"operating_margin": 0.14, "net_margin": 0.11},
        ),
    ]


def test_financial_chart_keeps_exact_values() -> None:
    figure = financial_trend_figure(_periods(), ["revenue", "net_income"])

    assert list(figure.data[0].y) == [800.0, 1_000.0]
    assert list(figure.data[1].y) == [80.0, 110.0]
    assert figure.layout.hovermode == "x unified"


def test_margin_chart_keeps_decimal_values_for_exact_hover() -> None:
    figure = margin_figure(_periods(), ["operating_margin", "net_margin"])

    assert list(figure.data[0].y) == [0.12, 0.14]
    assert figure.layout.yaxis.tickformat == ".0%"


def test_price_chart_preserves_zero_volume_and_exact_close() -> None:
    points = [
        PricePoint(date=date(2025, 1, 1), close=100.25, volume=0.0),
        PricePoint(date=date(2025, 1, 2), close=102.5, volume=1_200.0),
    ]

    figure = price_figure(points, symbol="RELIANCE.NS")

    assert list(figure.data[0].y) == [100.25, 102.5]
    assert figure.data[0].name == "RELIANCE.NS"


def test_comparison_chart_preserves_aligned_gaps() -> None:
    frame = pd.DataFrame(
        {
            "RELIANCE.NS": [100.0, 103.2],
            "TCS.NS": [100.0, None],
        },
        index=pd.to_datetime(["2025-01-01", "2025-01-02"]),
    )

    figure = comparison_figure(frame, y_title="Indexed price")

    assert list(figure.data[0].y) == [100.0, 103.2]
    assert pd.isna(figure.data[1].y[1])


def test_empty_chart_explains_unavailable_data() -> None:
    figure = financial_trend_figure([], ["revenue"])

    assert "unavailable" in figure.layout.annotations[0].text.lower()
