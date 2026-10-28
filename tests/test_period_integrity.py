from datetime import date

import pytest

from nivesh.domain.models import FinancialPeriod
from nivesh.services.normalization import enrich_periods


def quarters():
    return [
        FinancialPeriod(
            period_ending=date(y, m, d),
            net_income=10,
            free_cash_flow=5,
            total_equity=100,
            total_assets=200,
        )
        for y, m, d in [(2024, 3, 31), (2024, 6, 30), (2024, 9, 30), (2024, 12, 31), (2025, 3, 31)]
    ]


def test_quarterly_returns_require_complete_ttm_and_year_earlier_balance():
    result = enrich_periods(quarters(), frequency="quarter")
    assert result[-1].metrics["roe"] == pytest.approx(0.4)
    assert result[-1].metrics["roa"] == pytest.approx(0.2)
    assert result[-2].metrics["roe"] is None
    assert result[-1].metrics["revenue_cagr_3y"] is None


def test_negative_denominators_do_not_reward_quality():
    row = FinancialPeriod(
        period_ending=date(2025, 3, 31),
        net_income=-10,
        operating_cash_flow=-20,
        total_equity=-100,
        total_assets=-200,
    )
    metrics = enrich_periods([row])[-1].metrics
    assert metrics["roe"] is None
    assert metrics["roa"] is None
    assert metrics["cash_conversion"] is None


def test_cagr_requires_three_calendar_years_not_three_rows():
    rows = [FinancialPeriod(period_ending=date(2025, m, 1), revenue=100 + m) for m in [1, 4, 7, 10]]
    assert enrich_periods(rows)[-1].metrics["revenue_cagr_3y"] is None


def test_canonical_fundamentals_and_complete_ttm():
    from nivesh.services.fundamentals import fundamental_inputs

    inputs = fundamental_inputs(
        quarters(),
        {"market_cap": 1000, "enterprise_to_ebitda": 8, "return_on_equity": None},
        "quarter",
    )
    assert inputs["pe_ratio"] == 25
    assert inputs["fcf_yield"] == 0.02
    assert inputs["ev_to_ebitda"] == 8
    assert inputs["roe"] == 0.4
    assert fundamental_inputs(quarters()[::2], {"market_cap": 1000}, "quarter")["pe_ratio"] is None


def test_alias_units_and_statement_priority():
    from nivesh.services.fundamentals import fundamental_inputs

    rows = [
        FinancialPeriod(
            period_ending=date(2025, 3, 31), total_debt=0, total_equity=100, metrics={"roe": 0.15}
        )
    ]
    inputs = fundamental_inputs(
        rows,
        {
            "roe": None,
            "return_on_equity": 0.8,
            "debt_to_equity": 120,
            "debt_to_equity_percent": 120,
        },
        "annual",
    )
    assert inputs["roe"] == 0.15
    assert inputs["debt_equity"] == 0
    assert fundamental_inputs([], {"debt_to_equity_percent": 120}, "annual")["debt_equity"] == 1.2


def test_quarterly_missing_prior_balance_and_provider_roe_are_withheld():
    from nivesh.services.fundamentals import fundamental_inputs

    rows = quarters()
    rows[0] = rows[0].model_copy(update={"total_equity": None})
    assert enrich_periods(rows, "quarter")[-1].metrics["roe"] is None
    assert fundamental_inputs(rows[-1:], {"return_on_equity": 0.9}, "quarter")["roe"] is None


def test_finite_and_partial_latest_inputs():
    from nivesh.services.fundamentals import fundamental_inputs

    rows = quarters() + [FinancialPeriod(period_ending=date(2025, 6, 30), total_debt=0)]
    inputs = fundamental_inputs(
        rows, {"market_cap": float("inf"), "pe_ratio": float("nan")}, "quarter"
    )
    assert inputs["pe_ratio"] is None
    assert inputs["fcf_yield"] is None
    assert inputs["roe"] is None


def test_three_year_cagr_matches_calendar_date_with_missing_middle_year():
    rows = [
        FinancialPeriod(period_ending=date(y, 3, 31), revenue=r)
        for y, r in [(2022, 100), (2024, 121), (2025, 133.1)]
    ]
    assert enrich_periods(rows)[-1].metrics["revenue_cagr_3y"] == pytest.approx(0.1, abs=0.0001)


def test_null_normalized_metric_does_not_hide_computable_statement_value():
    from nivesh.services.fundamentals import fundamental_inputs

    row = FinancialPeriod(
        period_ending=date(2025, 3, 31), net_income=10, total_equity=100, metrics={"roe": None}
    )
    assert fundamental_inputs([row], {"return_on_equity": 0.9})["roe"] == 0.1


def test_negative_previous_equity_cannot_be_rescued_by_provider_ratio():
    from nivesh.services.fundamentals import fundamental_inputs

    rows = [
        FinancialPeriod(period_ending=date(2024, 3, 31), total_equity=-100),
        FinancialPeriod(period_ending=date(2025, 3, 31), total_equity=200, net_income=10),
    ]
    assert fundamental_inputs(rows, {"return_on_equity": 0.9})["roe"] is None


def test_extreme_cagr_inputs_are_unavailable_instead_of_crashing():
    rows = [FinancialPeriod(period_ending=date(2022,3,31), revenue=1e-300),
            FinancialPeriod(period_ending=date(2025,3,31), revenue=1e300)]
    assert enrich_periods(rows)[-1].metrics['revenue_cagr_3y'] is None
