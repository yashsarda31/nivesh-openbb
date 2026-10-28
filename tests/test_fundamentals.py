"""Invalid known balance denominators override provider ratio fallbacks."""

from datetime import date

import pytest

from nivesh.domain.models import FinancialPeriod
from nivesh.services.fundamentals import fundamental_inputs
from nivesh.services.scoring import score_company


@pytest.mark.parametrize("equity", [-100.0, 0.0])
def test_invalid_known_equity_with_missing_debt_withholds_provider_ratio(equity: float) -> None:
    row = FinancialPeriod(period_ending=date(2025, 3, 31), total_equity=equity)
    inputs = fundamental_inputs([row], {"debt_to_equity_ratio": 0.1})
    assert inputs["debt_equity"] is None
    score = score_company([row], {"debt_equity": 0.1}, sector="Industrials")
    assert score.components["balance"].score is None


def test_unknown_equity_preserves_provider_ratio_fallback() -> None:
    row = FinancialPeriod(period_ending=date(2025, 3, 31))
    assert fundamental_inputs([row], {"debt_equity": 0.1})["debt_equity"] == 0.1


@pytest.mark.parametrize("liabilities", [-100.0, 0.0])
def test_invalid_known_liabilities_withholds_liquidity_ratio(liabilities: float) -> None:
    row = FinancialPeriod(
        period_ending=date(2025, 3, 31),
        total_current_assets=-200.0,
        total_current_liabilities=liabilities,
    )
    assert fundamental_inputs([row], {"current_ratio": 2.0})["current_ratio"] is None
