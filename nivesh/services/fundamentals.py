"""Shared period-aware fundamental inputs for scoring and research."""

from collections.abc import Mapping, Sequence

from nivesh.domain.models import FinancialPeriod
from nivesh.services.normalization import _number, enrich_periods, sum_field, trailing_quarters
from nivesh.services.ratios import price_to_earnings, safe_divide

ALIASES = {
    "pe_ratio": ("pe_ratio", "price_earnings", "price_to_earnings", "trailing_pe"),
    "price_to_book": ("price_to_book", "pb_ratio", "price_book"),
    "ev_to_ebitda": ("ev_to_ebitda", "enterprise_to_ebitda", "enterprise_value_to_ebitda"),
    "roe": ("roe", "return_on_equity"),
    "roa": ("roa", "return_on_assets"),
    "debt_equity": ("debt_equity", "debt_to_equity_ratio", "debt_to_equity"),
    "market_cap": ("market_cap", "market_capitalization"),
}


def fundamental_inputs(
    periods: Sequence[FinancialPeriod],
    metrics: Mapping[str, float | None],
    frequency: str = "annual",
    market_cap: float | None = None,
) -> dict[str, float | None]:
    """Prefer latest statement facts; derive annual values only from complete flows."""
    inputs = {key: _number(value) for key, value in metrics.items()}
    for canonical, aliases in ALIASES.items():
        inputs[canonical] = next(
            (inputs[key] for key in aliases if inputs.get(key) is not None), None
        )
    if inputs.get("debt_equity") is None:
        inputs["debt_equity"] = safe_divide(_number(metrics.get("debt_to_equity_percent")), 100)
    rows = enrich_periods(periods, frequency)
    if rows:
        latest = rows[-1]
        # Explicit normalized metrics are statement facts too; do not discard
        # them merely because a partial endpoint lacks their raw inputs.
        original = max(periods, key=lambda row: row.period_ending)
        for key, value in original.metrics.items():
            if _number(value) is not None:
                inputs[key] = _number(value)
        for key, value in latest.metrics.items():
            if _number(value) is not None:
                inputs[key] = _number(value)
        for key, field in (("roe", "total_equity"), ("roa", "total_assets")):
            denominator = _number(getattr(latest, field))
            if denominator is not None and denominator <= 0:
                inputs[key] = None
            if denominator is not None and latest.net_income is not None:
                inputs[key] = latest.metrics.get(key)
            if frequency in {"quarter", "quarterly"}:
                inputs[key] = latest.metrics.get(key)
        if latest.net_income is not None and latest.net_income <= 0:
            inputs["cash_conversion"] = None
        if latest.total_debt is not None and latest.total_equity is not None:
            inputs["debt_equity"] = latest.metrics.get("debt_equity")
        if latest.total_equity is not None and latest.total_equity <= 0:
            inputs["debt_equity"] = None
        if latest.total_current_liabilities is not None and latest.total_current_liabilities <= 0:
            inputs["current_ratio"] = None
        cap = _number(market_cap) if market_cap is not None else inputs.get("market_cap")
        window = trailing_quarters(rows) if frequency in {"quarter", "quarterly"} else [latest]
        if inputs.get("pe_ratio") is None:
            inputs["pe_ratio"] = price_to_earnings(cap, sum_field(window, "net_income"))
        if inputs.get("fcf_yield") is None:
            inputs["fcf_yield"] = safe_divide(
                sum_field(window, "free_cash_flow"), cap if cap is not None and cap > 0 else None
            )
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            inputs[alias] = inputs.get(canonical)
    return inputs
