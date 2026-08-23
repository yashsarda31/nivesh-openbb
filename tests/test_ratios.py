from datetime import date

import pytest

from nivesh.domain.models import FinancialPeriod
from nivesh.services.normalization import enrich_periods
from nivesh.services.ratios import average_balance, cagr, safe_divide


def test_safe_divide_distinguishes_missing_and_zero() -> None:
    assert safe_divide(None, 10.0) is None
    assert safe_divide(0.0, 10.0) == 0.0
    assert safe_divide(10.0, 0.0) is None


def test_average_balance_uses_both_periods() -> None:
    assert average_balance(1_000.0, 900.0) == 950.0
    assert average_balance(1_000.0, None) == 1_000.0


def test_cagr_requires_positive_start_and_horizon() -> None:
    assert cagr(100.0, 172.8, 3.0) == pytest.approx(0.2)
    assert cagr(0.0, 172.8, 3.0) is None
    assert cagr(100.0, 172.8, 0.0) is None


def test_enrich_periods_adds_three_year_growth() -> None:
    periods = [
        FinancialPeriod(period_ending=date(year, 3, 31), revenue=revenue, diluted_eps=eps)
        for year, revenue, eps in [
            (2022, 100.0, 10.0),
            (2023, 120.0, 12.0),
            (2024, 144.0, 14.4),
            (2025, 172.8, 17.28),
        ]
    ]

    latest = enrich_periods(periods)[-1]

    assert latest.metrics["revenue_cagr_3y"] == pytest.approx(0.2, abs=0.001)
    assert latest.metrics["eps_cagr_3y"] == pytest.approx(0.2, abs=0.001)
