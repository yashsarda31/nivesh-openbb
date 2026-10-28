"""Exact-value alignment and sanitized payloads for company comparison."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from nivesh.domain.models import AnalysisBundle, FinancialPeriod
from nivesh.services.fundamentals import fundamental_inputs


class ComparisonRow(BaseModel):
    """One exact company/metric observation with its provenance."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    company: str
    metric: str
    label: str
    value: float | None
    display_value: str
    period: str | None
    currency: str | None
    provider: str
    warning: str | None = None


class TowerCompany(BaseModel):
    """Allow-listed, finite comparison data safe to send to the browser."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(max_length=24)
    name: str = Field(max_length=80)
    values: dict[str, float | None]


class ComparisonPayload(BaseModel):
    """All comparison views built from the same normalized analysis bundles."""

    model_config = ConfigDict(frozen=True)

    rows: list[ComparisonRow]
    towers: list[TowerCompany]
    warnings: tuple[str, ...] = ()


_STATEMENT_METRICS = {
    "revenue": ("Revenue", "money"),
    "net_income": ("Net income", "money"),
    "free_cash_flow": ("Free cash flow", "money"),
}
_RATIO_METRICS = {
    "operating_margin": ("Operating margin", "percent"),
    "roe": ("Return on equity", "percent"),
    "debt_equity": ("Debt / equity", "multiple"),
    "current_ratio": ("Current ratio", "multiple"),
}
_PROVIDER_METRICS = {
    "pe_ratio": ("P/E", "multiple"),
    "price_to_book": ("Price / book", "multiple"),
    "ev_to_ebitda": ("EV / EBITDA", "multiple"),
    "fcf_yield": ("Free cash flow yield", "percent"),
}


def normalized_price_frame(bundles: Sequence[AnalysisBundle]) -> pd.DataFrame:
    """Index all companies on the first shared positive close, without filling gaps."""

    series: list[pd.Series[float]] = []
    for bundle in bundles:
        points = sorted(bundle.prices.data, key=lambda point: point.date)
        values = pd.Series(
            data=[point.close if point.close > 0 else None for point in points],
            index=pd.to_datetime([point.date for point in points]),
            name=bundle.symbol,
            dtype="float64",
        )
        if values.index.has_duplicates:
            values = values.groupby(level=0).last()
        series.append(values)

    if not series:
        return pd.DataFrame()
    frame = pd.concat(series, axis=1, join="outer").sort_index()
    frame.index.name = "Date"
    common = frame.dropna(how="any")
    if common.empty:
        return frame.iloc[0:0]
    frame = frame.loc[common.index[0] :]
    return frame.divide(common.iloc[0], axis="columns") * 100.0


def build_comparison(bundles: Sequence[AnalysisBundle]) -> ComparisonPayload:
    """Build exact table rows and a finite Three.js-ready payload for 2-4 companies."""

    if not 2 <= len(bundles) <= 4:
        raise ValueError("Comparison requires two to four companies.")
    symbols = [bundle.symbol for bundle in bundles]
    if len(set(symbols)) != len(symbols):
        raise ValueError("Comparison companies must be unique.")
    frequencies = {bundle.statements.period for bundle in bundles}
    if len(frequencies) != 1 or not frequencies <= {"annual", "quarterly"}:
        raise ValueError(
            "Use the same reporting frequency for every company. "
            "Re-analyze the selected companies as Annual or Quarterly."
        )

    rows: list[ComparisonRow] = []
    towers: list[TowerCompany] = []
    warnings: list[str] = []
    for bundle in bundles:
        latest = max(
            bundle.statements.data,
            key=lambda item: item.period_ending,
            default=None,
        )
        rows.extend(_company_rows(bundle, latest))
        tower = _tower_company(bundle)
        towers.append(tower)
        rows.extend(_score_rows(bundle, latest, tower))
        warnings.extend(
            f"{bundle.symbol}: {warning}"
            for warning in (*bundle.statements.warnings, *bundle.metrics.warnings)
        )
    return ComparisonPayload(rows=rows, towers=towers, warnings=tuple(dict.fromkeys(warnings)))


def _company_rows(bundle: AnalysisBundle, latest: FinancialPeriod | None) -> list[ComparisonRow]:
    profile = bundle.profile.data
    company = profile.name or bundle.symbol
    period_label = _period_label(latest)
    rows: list[ComparisonRow] = []
    provider_inputs = fundamental_inputs([], bundle.metrics.data)
    inputs = fundamental_inputs(
        bundle.statements.data,
        bundle.metrics.data,
        bundle.statements.period or "annual",
        market_cap=profile.market_cap,
    )

    for key, (label, format_kind) in _STATEMENT_METRICS.items():
        value = _finite(getattr(latest, key, None)) if latest else None
        rows.append(
            _row(
                bundle,
                company,
                key,
                label,
                value,
                format_kind,
                period_label,
                bundle.statements.provider,
                bundle.statements.currency,
                bundle.statements.warnings,
            )
        )
    for key, (label, format_kind) in _RATIO_METRICS.items():
        value = _finite(latest.metrics.get(key)) if latest else None
        rows.append(
            _row(
                bundle,
                company,
                key,
                label,
                value,
                format_kind,
                period_label,
                bundle.statements.provider,
                bundle.statements.currency,
                bundle.statements.warnings,
            )
        )
    for key, (label, format_kind) in _PROVIDER_METRICS.items():
        value = _finite(inputs.get(key))
        derived = value is not None and provider_inputs.get(key) is None
        source_period = (
            f"{'TTM ending' if bundle.statements.period == 'quarterly' else 'Annual ending'} "
            f"{latest.period_ending}"
            if derived and latest
            else str(bundle.metrics.as_of)
            if bundle.metrics.as_of
            else "Source date unavailable"
        )
        rows.append(
            _row(
                bundle,
                company,
                key,
                label,
                value,
                format_kind,
                source_period,
                f"Nivesh derived · {bundle.statements.provider}"
                if derived
                else bundle.metrics.provider,
                bundle.metrics.currency,
                bundle.metrics.warnings,
            )
        )
    return rows


def _row(
    bundle: AnalysisBundle,
    company: str,
    metric: str,
    label: str,
    value: float | None,
    format_kind: str,
    period: str | None,
    provider: str,
    currency: str | None,
    warnings: Sequence[str],
) -> ComparisonRow:
    return ComparisonRow(
        symbol=bundle.symbol,
        company=company,
        metric=metric,
        label=label,
        value=value,
        display_value=_display(value, format_kind, currency),
        period=period,
        currency=currency,
        provider=provider,
        warning=" · ".join(warnings) or None,
    )


def _tower_company(bundle: AnalysisBundle) -> TowerCompany:
    scorecard = bundle.scorecard
    values: dict[str, float | None] = {
        "composite": _finite(scorecard.composite if scorecard else None),
        "quality": _component_value(bundle, "quality"),
        "growth": _component_value(bundle, "growth"),
        "balance_sheet": _component_value(bundle, "balance"),
        "valuation": _component_value(bundle, "valuation"),
    }
    return TowerCompany(
        symbol=bundle.symbol[:24],
        name=(bundle.profile.data.name or bundle.symbol)[:80],
        values=values,
    )


def _score_rows(
    bundle: AnalysisBundle,
    latest: FinancialPeriod | None,
    tower: TowerCompany,
) -> list[ComparisonRow]:
    scorecard = bundle.scorecard
    provider = f"Nivesh {scorecard.methodology_version}" if scorecard else "Nivesh"
    warnings = scorecard.warnings if scorecard else ("Scorecard unavailable",)
    labels = {
        "composite": "Composite score",
        "quality": "Quality score",
        "growth": "Growth score",
        "balance_sheet": "Balance-sheet score",
        "valuation": "Valuation score",
    }
    company = bundle.profile.data.name or bundle.symbol
    return [
        _row(
            bundle,
            company,
            metric,
            labels[metric],
            value,
            "score",
            _period_label(latest),
            provider,
            None,
            warnings,
        )
        for metric, value in tower.values.items()
    ]


def _component_value(bundle: AnalysisBundle, name: str) -> float | None:
    if bundle.scorecard is None:
        return None
    component = bundle.scorecard.components.get(name)
    return _finite(component.score if component else None)


def _period_label(period: FinancialPeriod | None) -> str | None:
    if period is None:
        return None
    return f"{period.fiscal_period or 'Period'} {period.fiscal_year or period.period_ending.year}"


def _finite(value: float | int | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if isfinite(number) else None


def _display(value: float | None, format_kind: str, currency: str | None) -> str:
    if value is None:
        return "—"
    if format_kind == "percent":
        return f"{value:.1%}"
    if format_kind == "multiple":
        return f"{value:.2f}×"
    if format_kind == "score":
        return f"{value:.0f} / 100"
    prefix = "₹ " if currency == "INR" else ""
    return f"{prefix}{value / 10_000_000:,.0f} Cr"
