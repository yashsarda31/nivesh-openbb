"""Transparent, coverage-aware scoring for fundamental analysis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from nivesh.domain.models import (
    ComponentScore,
    FinancialPeriod,
    MetricScore,
    Scorecard,
)
from nivesh.services.fundamentals import fundamental_inputs

Direction = Literal["higher", "lower"]


@dataclass(frozen=True)
class MetricRule:
    """One documented fixed-band transformation within a score component."""

    key: str
    label: str
    weight: float
    direction: Direction
    bands: tuple[float, float, float, float, float]
    aliases: tuple[str, ...] = ()
    positive_only: bool = False


COMPONENT_RULES: dict[str, tuple[MetricRule, ...]] = {
    "quality": (
        MetricRule("roe", "Return on equity", 0.35, "higher", (-0.05, 0.05, 0.12, 0.20, 0.30)),
        MetricRule(
            "operating_margin",
            "Operating margin",
            0.35,
            "higher",
            (-0.05, 0.05, 0.12, 0.20, 0.30),
        ),
        MetricRule(
            "cash_conversion",
            "Cash conversion",
            0.30,
            "higher",
            (0.0, 0.5, 0.8, 1.0, 1.3),
        ),
    ),
    "growth": (
        MetricRule(
            "revenue_cagr_3y",
            "Revenue CAGR (3Y)",
            0.50,
            "higher",
            (-0.05, 0.0, 0.08, 0.15, 0.25),
        ),
        MetricRule(
            "eps_cagr_3y",
            "EPS CAGR (3Y)",
            0.50,
            "higher",
            (-0.10, 0.0, 0.10, 0.20, 0.35),
        ),
    ),
    "balance": (
        MetricRule(
            "debt_equity",
            "Debt to equity",
            0.60,
            "lower",
            (3.0, 2.0, 1.0, 0.5, 0.0),
        ),
        MetricRule(
            "current_ratio",
            "Current ratio",
            0.40,
            "higher",
            (0.5, 0.8, 1.2, 1.8, 2.5),
        ),
    ),
    "valuation": (
        MetricRule(
            "pe_ratio",
            "Price to earnings",
            0.35,
            "lower",
            (50.0, 35.0, 25.0, 18.0, 10.0),
            aliases=("price_earnings", "price_to_earnings"),
            positive_only=True,
        ),
        MetricRule(
            "price_to_book",
            "Price to book",
            0.20,
            "lower",
            (10.0, 6.0, 4.0, 2.0, 1.0),
            aliases=("pb_ratio", "price_book"),
            positive_only=True,
        ),
        MetricRule(
            "ev_to_ebitda",
            "EV to EBITDA",
            0.25,
            "lower",
            (30.0, 22.0, 15.0, 10.0, 6.0),
            aliases=("enterprise_value_to_ebitda",),
            positive_only=True,
        ),
        MetricRule(
            "fcf_yield",
            "Free cash flow yield",
            0.20,
            "higher",
            (0.0, 0.01, 0.03, 0.05, 0.08),
        ),
    ),
}

COMPONENT_WEIGHT = 0.25
MIN_COMPONENT_COVERAGE = 0.50
MIN_COMPOSITE_COVERAGE = 0.60
MIN_COMPOSITE_COMPONENTS = 3
METHODOLOGY_VERSION = "nivesh-v1"


def transform_metric(
    value: float | None,
    bands: tuple[float, float, float, float, float],
    direction: Direction,
) -> float | None:
    """Map a value to 0-100 using five ordered anchors and linear interpolation."""

    if value is None:
        return None

    ascending = direction == "higher"
    ordered_correctly = bands[0] < bands[-1] if ascending else bands[0] > bands[-1]
    if not ordered_correctly:
        raise ValueError(f"Bands must improve in the {direction} direction")

    if (ascending and value <= bands[0]) or (not ascending and value >= bands[0]):
        return 0.0
    if (ascending and value >= bands[-1]) or (not ascending and value <= bands[-1]):
        return 100.0

    for index, (lower_score_value, higher_score_value) in enumerate(
        zip(bands, bands[1:], strict=True)
    ):
        in_interval = (
            lower_score_value <= value <= higher_score_value
            if ascending
            else higher_score_value <= value <= lower_score_value
        )
        if in_interval:
            interval = abs(higher_score_value - lower_score_value)
            progress = abs(value - lower_score_value) / interval
            return index * 25.0 + progress * 25.0

    raise RuntimeError("Metric value did not match a scoring interval")


def score_company(
    periods: Sequence[FinancialPeriod],
    provider_metrics: Mapping[str, float | None],
    *,
    sector: str | None,
    frequency: str = "annual",
) -> Scorecard:
    """Build a scorecard without publishing scores below coverage thresholds."""

    latest = max(periods, key=lambda period: period.period_ending) if periods else None
    source_period = _source_period(latest)
    inputs = fundamental_inputs(periods, provider_metrics, frequency)

    financial_company = _is_financial_sector(sector)
    components: dict[str, ComponentScore] = {}
    for name, rules in COMPONENT_RULES.items():
        if name == "balance" and financial_company:
            components[name] = _financial_balance_exclusion(rules)
            continue
        components[name] = _score_component(name, rules, inputs, source_period)

    eligible = [component for component in components.values() if component.target_weight > 0]
    total_target = sum(component.target_weight for component in eligible)
    coverage = (
        sum(component.target_weight * component.coverage for component in eligible) / total_target
        if total_target
        else 0.0
    )
    published = [component for component in eligible if component.score is not None]

    warnings: list[str] = []
    composite: int | None = None
    if len(published) >= MIN_COMPOSITE_COMPONENTS and coverage >= MIN_COMPOSITE_COVERAGE:
        published_weight = sum(component.target_weight for component in published)
        composite = round(
            sum(
                component.score * component.target_weight
                for component in published
                if component.score is not None
            )
            / published_weight
        )
    else:
        warnings.append(
            "Composite withheld: requires at least three published components "
            "and 60% input coverage."
        )

    return Scorecard(
        composite=composite,
        coverage=coverage,
        components=components,
        methodology_version=METHODOLOGY_VERSION,
        warnings=tuple(warnings),
    )


def _score_component(
    name: str,
    rules: Sequence[MetricRule],
    inputs: Mapping[str, float | None],
    source_period: str | None,
) -> ComponentScore:
    metric_scores: dict[str, MetricScore] = {}
    available_weight = 0.0

    for rule in rules:
        raw_value = _first_value(inputs, (rule.key, *rule.aliases))
        excluded_reason: str | None = None
        if rule.positive_only and raw_value is not None and raw_value <= 0:
            raw_value = None
            excluded_reason = "Not meaningful when negative"
        score = transform_metric(raw_value, rule.bands, rule.direction)
        if score is not None:
            available_weight += rule.weight
        elif excluded_reason is None:
            excluded_reason = "Unavailable from provider"
        metric_scores[rule.key] = MetricScore(
            name=rule.key,
            label=rule.label,
            raw_value=raw_value,
            score=score,
            direction=rule.direction,
            source_period=source_period,
            excluded_reason=excluded_reason,
        )

    total_weight = sum(rule.weight for rule in rules)
    coverage = available_weight / total_weight if total_weight else 0.0
    if available_weight:
        weights = {rule.key: rule.weight / available_weight for rule in rules}
        metric_scores = {
            key: metric.model_copy(
                update={
                    "effective_weight": weights[key] if metric.score is not None else 0.0,
                }
            )
            for key, metric in metric_scores.items()
        }

    component_score: int | None = None
    warnings: list[str] = []
    if coverage >= MIN_COMPONENT_COVERAGE:
        component_score = round(
            sum(
                metric.score * metric.effective_weight
                for metric in metric_scores.values()
                if metric.score is not None
            )
        )
    else:
        warnings.append("Score withheld: less than 50% of configured input weight is available.")

    return ComponentScore(
        name=name,
        score=component_score,
        coverage=coverage,
        target_weight=COMPONENT_WEIGHT,
        metrics=metric_scores,
        excluded=tuple(key for key, metric in metric_scores.items() if metric.score is None),
        warnings=tuple(warnings),
    )


def _financial_balance_exclusion(rules: Sequence[MetricRule]) -> ComponentScore:
    reason = "Sector rule: non-comparable for financial companies"
    metrics = {
        rule.key: MetricScore(
            name=rule.key,
            label=rule.label,
            direction=rule.direction,
            excluded_reason=reason,
        )
        for rule in rules
    }
    return ComponentScore(
        name="balance",
        score=None,
        coverage=0.0,
        target_weight=0.0,
        metrics=metrics,
        excluded=tuple(metrics),
        warnings=(reason,),
    )


def _first_value(inputs: Mapping[str, float | None], keys: Sequence[str]) -> float | None:
    for key in keys:
        value = inputs.get(key)
        if value is not None:
            return value
    return None


def _derive_fcf_yield(
    latest: FinancialPeriod, provider_metrics: Mapping[str, float | None]
) -> float | None:
    market_cap = _first_value(provider_metrics, ("market_cap", "market_capitalization"))
    if latest.free_cash_flow is None or market_cap is None or market_cap <= 0:
        return None
    return latest.free_cash_flow / market_cap


def _source_period(period: FinancialPeriod | None) -> str | None:
    if period is None:
        return None
    label = period.fiscal_period or "Period"
    year = period.fiscal_year or period.period_ending.year
    return f"{label} {year}"


def _is_financial_sector(sector: str | None) -> bool:
    normalized = (sector or "").casefold()
    return any(term in normalized for term in ("financial", "bank", "insurance", "capital markets"))
