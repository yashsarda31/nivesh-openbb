"""Contract tests for the transparent Nivesh scoring methodology."""

from __future__ import annotations

from datetime import date

import pytest

from nivesh.domain.models import FinancialPeriod
from nivesh.services.scoring import score_company, transform_metric


def _latest_period(**metrics: float | None) -> FinancialPeriod:
    return FinancialPeriod(
        period_ending=date(2026, 3, 31),
        fiscal_period="FY",
        fiscal_year=2026,
        metrics=metrics,
    )


def test_transform_metric_uses_documented_fixed_bands() -> None:
    assert transform_metric(0.12, (-0.05, 0.05, 0.12, 0.20, 0.30), "higher") == 50
    assert transform_metric(0.25, (-0.05, 0.05, 0.12, 0.20, 0.30), "higher") == pytest.approx(87.5)
    assert transform_metric(18, (50, 35, 25, 18, 10), "lower") == 75
    assert transform_metric(None, (0, 1, 2, 3, 4), "higher") is None


def test_publishes_complete_components_and_composite() -> None:
    period = _latest_period(
        roe=0.20,
        operating_margin=0.20,
        cash_conversion=1.0,
        revenue_cagr_3y=0.15,
        eps_cagr_3y=0.20,
        debt_equity=0.5,
        current_ratio=1.8,
    )

    scorecard = score_company(
        [period],
        {"pe_ratio": 18, "price_to_book": 2, "ev_to_ebitda": 10, "fcf_yield": 0.05},
        sector="Industrials",
    )

    assert scorecard.composite == 75
    assert scorecard.coverage == 1.0
    assert set(scorecard.components) == {"quality", "growth", "balance", "valuation"}
    assert all(component.score == 75 for component in scorecard.components.values())
    assert all(component.coverage == 1.0 for component in scorecard.components.values())


def test_component_is_withheld_below_half_weight_coverage() -> None:
    period = _latest_period(roe=0.20)

    scorecard = score_company([period], {}, sector="Industrials")

    quality = scorecard.components["quality"]
    assert quality.coverage == pytest.approx(0.35)
    assert quality.score is None
    assert scorecard.composite is None
    assert "operating_margin" in quality.excluded
    assert quality.metrics["roe"].source_period == "FY 2026"


def test_negative_valuation_multiples_are_unavailable() -> None:
    scorecard = score_company(
        [_latest_period()],
        {"pe_ratio": -12, "price_to_book": 3, "ev_to_ebitda": -4},
        sector="Technology",
    )

    valuation = scorecard.components["valuation"]
    assert valuation.metrics["pe_ratio"].score is None
    assert valuation.metrics["pe_ratio"].excluded_reason == "Not meaningful when negative"
    assert valuation.metrics["ev_to_ebitda"].score is None
    assert valuation.coverage == pytest.approx(0.20)
    assert valuation.score is None


def test_financial_sector_excludes_non_comparable_balance_component() -> None:
    period = _latest_period(
        roe=0.20,
        operating_margin=0.20,
        cash_conversion=1.0,
        revenue_cagr_3y=0.15,
        eps_cagr_3y=0.20,
        debt_equity=8.0,
        current_ratio=0.2,
    )

    scorecard = score_company(
        [period],
        {"pe_ratio": 18, "price_to_book": 2, "ev_to_ebitda": 10, "fcf_yield": 0.05},
        sector="Financial Services",
    )

    balance = scorecard.components["balance"]
    assert balance.score is None
    assert balance.coverage == 0.0
    assert balance.target_weight == 0.0
    assert "Sector rule: non-comparable for financial companies" in balance.warnings
    assert scorecard.composite == 75
    assert scorecard.coverage == 1.0


def test_composite_needs_three_components_and_sixty_percent_coverage() -> None:
    period = _latest_period(
        roe=0.20,
        operating_margin=0.20,
        cash_conversion=1.0,
        revenue_cagr_3y=0.15,
        eps_cagr_3y=0.20,
    )

    scorecard = score_company([period], {}, sector="Industrials")

    assert scorecard.components["quality"].score == 75
    assert scorecard.components["growth"].score == 75
    assert scorecard.composite is None
    assert scorecard.coverage == 0.5
    assert "Composite withheld" in scorecard.warnings[0]
