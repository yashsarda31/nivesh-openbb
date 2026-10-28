"""Normalize OpenBB statement records into aligned financial periods."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from math import isfinite
from typing import Any

from nivesh.domain.models import FinancialPeriod
from nivesh.services.ratios import average_balance, cagr, safe_divide

INCOME_FIELDS = {
    # openbb-yfinance reports revenue as total_revenue / operating_revenue.
    "revenue": "revenue",
    "total_revenue": "revenue",
    "operating_revenue": "revenue",
    "operating_income": "operating_income",
    "ebitda": "ebitda",
    "net_income": "net_income",
    "diluted_earnings_per_share": "diluted_eps",
    "diluted_eps": "diluted_eps",
}
BALANCE_FIELDS = {
    "total_assets": "total_assets",
    # openbb-yfinance has no total_equity key; these are its equity variants,
    # ordered from the most faithful to the loosest definition.
    "total_equity": "total_equity",
    "stockholders_equity": "total_equity",
    "common_stock_equity": "total_equity",
    "total_common_equity": "total_equity",
    "total_equity_non_controlling_interests": "total_equity",
    "total_debt": "total_debt",
    "cash_and_cash_equivalents": "cash",
    "cash_and_equivalents": "cash",
    "total_current_assets": "total_current_assets",
    "total_current_liabilities": "total_current_liabilities",
}
CASH_FIELDS = {
    "operating_cash_flow": "operating_cash_flow",
    "capital_expenditure": "capital_expenditure",
    "capital_expenditures": "capital_expenditure",
    "free_cash_flow": "free_cash_flow",
}


def _date_value(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None
    return number if isfinite(number) else None


def _merge_records(
    target: dict[date, dict[str, Any]],
    records: Sequence[Mapping[str, Any]],
    field_map: Mapping[str, str],
) -> None:
    for record in records:
        period_ending = _date_value(record.get("period_ending"))
        if period_ending is None:
            continue
        row = target.setdefault(period_ending, {"period_ending": period_ending})
        fiscal_period = record.get("fiscal_period")
        fiscal_year = record.get("fiscal_year")
        currency = record.get("reported_currency") or record.get("currency")
        if fiscal_period not in {None, ""}:
            row["fiscal_period"] = str(fiscal_period)
        if (year := _number(fiscal_year)) is not None:
            row["fiscal_year"] = int(year)
        if currency not in {None, ""}:
            row["currency"] = str(currency)
        for source, destination in field_map.items():
            # Multiple source keys may target one destination (provider naming
            # variants). Map order is the priority: the first non-None value wins.
            if row.get(destination) is not None:
                continue
            if source in record:
                value = _number(record[source])
                if value is not None:
                    row[destination] = value


def normalize_statements(
    income: Sequence[Mapping[str, Any]],
    balance: Sequence[Mapping[str, Any]],
    cash: Sequence[Mapping[str, Any]],
) -> list[FinancialPeriod]:
    """Align statements on exact reporting dates without filling missing values."""

    rows: dict[date, dict[str, Any]] = {}
    _merge_records(rows, income, INCOME_FIELDS)
    _merge_records(rows, balance, BALANCE_FIELDS)
    _merge_records(rows, cash, CASH_FIELDS)
    return [FinancialPeriod.model_validate(rows[key]) for key in sorted(rows)]


def enrich_periods(
    periods: Sequence[FinancialPeriod], frequency: str = "annual"
) -> list[FinancialPeriod]:
    """Add deterministic ratios and growth metrics to normalized periods."""

    ordered = sorted(periods, key=lambda item: item.period_ending)
    enriched: list[FinancialPeriod] = []
    for index, period in enumerate(ordered):
        previous = comparable_period(ordered[:index], period)
        quarterly = frequency in {"quarter", "quarterly"}
        window = trailing_quarters(ordered[: index + 1]) if quarterly else [period]
        income = sum_field(window, "net_income")
        if quarterly and previous is None:
            income = None
        equity = positive_average(period.total_equity, previous.total_equity if previous else None)
        assets = positive_average(period.total_assets, previous.total_assets if previous else None)
        if quarterly:
            if previous is None or previous.total_equity is None:
                equity = None
            if previous is None or previous.total_assets is None:
                assets = None
        free_cash_flow = period.free_cash_flow
        if (
            free_cash_flow is None
            and period.operating_cash_flow is not None
            and period.capital_expenditure is not None
        ):
            # Providers disagree on capex sign, so use its absolute cash outflow.
            free_cash_flow = period.operating_cash_flow - abs(period.capital_expenditure)

        metrics = dict(period.metrics)
        metrics.update(
            {
                "operating_margin": safe_divide(period.operating_income, period.revenue),
                "net_margin": safe_divide(period.net_income, period.revenue),
                "roe": safe_divide(
                    income,
                    equity,
                ),
                "roa": safe_divide(
                    income,
                    assets,
                ),
                "debt_equity": safe_divide(
                    period.total_debt, positive_average(period.total_equity, None)
                ),
                "current_ratio": safe_divide(
                    period.total_current_assets,
                    positive_average(period.total_current_liabilities, None),
                ),
                "cash_conversion": safe_divide(
                    period.operating_cash_flow, positive_average(period.net_income, None)
                ),
            }
        )
        baseline = comparable_period(ordered[:index], period, years=3)
        if baseline is not None:
            years = (period.period_ending - baseline.period_ending).days / 365.2425
            metrics["revenue_cagr_3y"] = cagr(baseline.revenue, period.revenue, years)
            metrics["eps_cagr_3y"] = cagr(baseline.diluted_eps, period.diluted_eps, years)
        else:
            metrics["revenue_cagr_3y"] = None
            metrics["eps_cagr_3y"] = None
        enriched.append(
            period.model_copy(update={"free_cash_flow": free_cash_flow, "metrics": metrics})
        )
    return enriched


def comparable_period(
    periods: Sequence[FinancialPeriod], current: FinancialPeriod, years: int = 1
) -> FinancialPeriod | None:
    """Find the same reporting date, allowing leap-day month ends."""
    target = current.period_ending
    for row in periods:
        day_matches = row.period_ending.day == target.day or (
            target.month == 2 and row.period_ending.day >= 28 and target.day >= 28
        )
        if (
            row.period_ending.year == target.year - years
            and row.period_ending.month == target.month
            and day_matches
        ):
            return row
    return None


def trailing_quarters(periods: Sequence[FinancialPeriod]) -> list[FinancialPeriod]:
    """Return four contiguous quarters ending at the newest observation."""
    rows = sorted(periods, key=lambda row: row.period_ending)[-4:]
    if len(rows) != 4:
        return []
    for earlier, later in zip(rows, rows[1:], strict=False):
        months = (
            (later.period_ending.year - earlier.period_ending.year) * 12
            + later.period_ending.month
            - earlier.period_ending.month
        )
        if months != 3 or not 75 <= (later.period_ending - earlier.period_ending).days <= 105:
            return []
    return rows


def sum_field(periods: Sequence[FinancialPeriod], field: str) -> float | None:
    """Sum complete finite flow observations."""
    values = [_number(getattr(row, field)) for row in periods]
    if not values or any(value is None for value in values):
        return None
    return _number(sum(value for value in values if value is not None))


def positive_average(current: float | None, previous: float | None) -> float | None:
    """Reject nonpositive denominators, including either average endpoint."""
    current = _number(current)
    previous = _number(previous)
    if current is None or current <= 0 or (previous is not None and previous <= 0):
        return None
    return average_balance(current, previous)
