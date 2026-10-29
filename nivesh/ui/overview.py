"""Single-company identity, key metrics, price history, and data health."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from math import isclose
from typing import Any, Literal

import pandas as pd
import streamlit as st

from nivesh.domain.models import (
    AnalysisBundle,
    DatasetResult,
    FinancialPeriod,
    PricePoint,
)
from nivesh.services.fundamentals import ALIASES, fundamental_inputs
from nivesh.services.normalization import comparable_period, enrich_periods
from nivesh.ui import kit
from nivesh.ui.charts import price_figure
from nivesh.ui.research import render_research

Getter = Callable[[FinancialPeriod], float | None]
DeltaKind = Literal["growth", "points", "multiple"]

_STATUS_TONES: dict[str, kit.Tone] = {
    "Available": "ok",
    "Partial": "warn",
    "Source date unknown": "warn",
    "Stale": "warn",
    "Unavailable": "bad",
}


def render_company_header(bundle: AnalysisBundle, *, actions: Callable[[], None]) -> None:
    """Identity, latest close and composite score, shared by every workspace view."""

    profile = bundle.profile.data
    ordered = sorted(bundle.prices.data, key=_price_date)
    last = ordered[-1] if ordered else None
    prior = ordered[-2] if len(ordered) > 1 else None
    change = last.close / prior.close - 1 if last and prior and prior.close > 0 else None
    tags = [bundle.symbol, *(v for v in (profile.exchange, profile.sector, profile.industry) if v)]
    latest = _latest_period(bundle)
    frequency = bundle.statements.period or "annual"
    with st.container(key="company-header"):
        with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
            st.html(kit.monogram(bundle.symbol), width="content")
            with st.container(key="company-identity", gap=None):
                st.subheader(profile.name or bundle.symbol, anchor=False)
                st.html(kit.chips(tags))
            st.html(
                kit.quote_block(
                    currency=bundle.prices.currency or profile.currency,
                    close=last.close if last else None,
                    change=change,
                    caption=f"Last close · {_price_date(last):%d %b %Y}" if last else "Last close",
                ),
                width="content",
            )
            st.html(
                kit.score_ring(bundle.scorecard.composite if bundle.scorecard else None),
                width="content",
            )
        with st.container(
            key="company-actions", horizontal=True, vertical_alignment="center", gap="small"
        ):
            actions()
            st.space("stretch")
            st.caption(
                f"{frequency.capitalize()} statements · latest period "
                f"{latest.period_ending if latest else 'unknown'} · {bundle.statements.provider}"
            )


def render_overview(bundle: AnalysisBundle) -> None:
    """Render the analyst overview without hiding unavailable values."""

    profile = bundle.profile.data
    latest = _latest_period(bundle)
    frequency = bundle.statements.period or "annual"
    ratios = fundamental_inputs(
        bundle.statements.data, bundle.metrics.data, frequency, profile.market_cap
    )
    history = enrich_periods(bundle.statements.data, frequency)
    provider_metrics = bundle.metrics.data
    scorecard = bundle.scorecard

    pe_value = ratios.get("pe_ratio")
    pe_derived = (
        not any(provider_metrics.get(key) is not None for key in ALIASES["pe_ratio"])
        and pe_value is not None
    )
    if pe_value is not None and pe_value <= 0:
        pe_value = None

    revenue = latest.revenue if latest else None
    # One wrapping row: three cards per line on desktop, two on phones.
    grid = st.container(key="kpi-grid", horizontal=True, gap="small")
    cells = [grid] * 6
    with cells[0]:
        st.metric(
            "Nivesh score",
            _format_score(scorecard.composite if scorecard else None),
            f"{scorecard.coverage:.0%} input coverage" if scorecard else None,
            delta_color="off",
            delta_arrow="off",
            help="A research score, not a recommendation. Review input coverage in Score.",
            border=True,
            height="stretch",
        )
    with cells[1]:
        metric_card(
            "Revenue",
            format_compact_money(revenue, profile.currency),
            f"Revenue for the latest reported {frequency} period; not necessarily TTM. "
            f"Exact: {_format_money(revenue, profile.currency)}.",
            history,
            lambda row: row.revenue,
            shown=revenue,
            kind="growth",
        )
    with cells[2]:
        metric_card(
            "ROE",
            _format_percent(ratios.get("roe")),
            "Return on equity; see the basis below.",
            history,
            lambda row: row.metrics.get("roe"),
            shown=ratios.get("roe"),
        )
    with cells[3]:
        metric_card(
            "Operating margin",
            _format_percent(ratios.get("operating_margin")),
            "Operating income divided by revenue for the reported period.",
            history,
            lambda row: row.metrics.get("operating_margin"),
            shown=ratios.get("operating_margin"),
        )
    with cells[4]:
        st.metric(
            "P/E",
            _format_pe(pe_value, derived=pe_derived),
            help="Provider multiple, or a statement-derived estimate marked with ≈.",
            border=True,
            height="stretch",
        )
    with cells[5]:
        metric_card(
            "Debt / equity",
            _format_multiple(ratios.get("debt_equity")),
            "Total debt relative to equity; not a bank capital-adequacy measure.",
            history,
            lambda row: row.metrics.get("debt_equity"),
            shown=ratios.get("debt_equity"),
            kind="multiple",
            chart="line",
            inverse=True,
        )

    roe_basis = (
        "TTM with average year-ago equity"
        if frequency in {"quarter", "quarterly"}
        else "annual with average equity where available"
    )
    st.caption(
        f"{frequency} · latest period {latest.period_ending if latest else 'unknown'} · "
        f"{bundle.statements.provider} · ROE basis: {roe_basis} · Sparklines plot reported "
        "periods; deltas compare the same period one year earlier."
    )
    st.caption("Research support, not a recommendation. Review coverage and source dates.")
    left, right = st.columns([2, 1], vertical_alignment="top")
    with left, st.container(key="card-price"):
        render_price_history(bundle)
    with right, st.container(key="card-readiness", height="stretch"):
        _render_readiness(bundle)

    render_data_health(bundle)
    st.space("small")
    render_research(bundle)


def _render_readiness(bundle: AnalysisBundle) -> None:
    profile = bundle.profile.data
    st.markdown("**Research readiness**")
    datasets: list[tuple[str, DatasetResult[Any]]] = [
        ("Profile", bundle.profile),
        ("Prices", bundle.prices),
        ("Statements", bundle.statements),
        ("Metrics", bundle.metrics),
    ]
    if any(ds.stale for _, ds in datasets):
        st.badge("Older source records", icon=":material/schedule:", color="orange")
    elif any(ds.coverage < 1 or ds.as_of is None for _, ds in datasets):
        st.badge("Review data gaps", icon=":material/info:", color="orange")
    else:
        st.badge("Source dates available", icon=":material/fact_check:", color="green")
    rows: list[tuple[str, kit.Tone, str, str]] = []
    for label, result in datasets:
        status = _dataset_status(result)
        rows.append((label, _STATUS_TONES[status], status, _dataset_caption(result)))
    st.html(kit.status_list(rows))
    if bundle.scorecard:
        st.progress(
            bundle.scorecard.coverage,
            text=f"{bundle.scorecard.coverage:.0%} score input coverage",
        )
    st.caption("Coverage measures available inputs, not confidence or investment quality.")
    st.markdown("**Company context**")
    st.html(
        kit.key_values(
            [
                ("Industry", profile.industry or "Unavailable"),
                ("Market cap", _format_money(profile.market_cap, profile.currency)),
                ("Currency", profile.currency or "Unavailable"),
            ]
        )
    )
    with st.expander("About the business"):
        st.write(profile.description or "Company description unavailable from provider.")
    if profile.website:
        st.link_button(
            "Company website",
            profile.website,
            icon=":material/open_in_new:",
            type="tertiary",
        )


def metric_card(
    label: str,
    value: str,
    help_text: str,
    history: Sequence[FinancialPeriod],
    getter: Getter,
    *,
    shown: float | None,
    kind: DeltaKind = "points",
    chart: Literal["line", "bar", "area"] = "area",
    inverse: bool = False,
) -> None:
    """Metric card with a reported-period sparkline and a same-period-last-year delta."""
    series = [point for point in (getter(row) for row in history) if point is not None]
    delta = note = None
    flat = False
    comparison = _year_ago(history, getter)
    # Describe movement only when the card shows the same statement value.
    if comparison and shown is not None and isclose(comparison[0], shown, rel_tol=1e-9):
        current, previous, prior = comparison
        if kind == "growth":
            move = current / previous - 1 if previous > 0 else None
            delta = f"{move:+.1%}" if move is not None else None
            flat = move is not None and round(move, 3) == 0
        elif kind == "multiple":
            delta = f"{current - previous:+.2f}×"
            flat = round(current - previous, 2) == 0
        else:
            delta = f"{(current - previous) * 100:+.1f} pp"
            flat = round((current - previous) * 100, 1) == 0
        if delta and flat:
            # A rounded zero is not movement; drop the sign, arrow and colour.
            delta = delta.lstrip("+-")
        note = f"vs {prior.period_ending:%b %Y}" if delta else None
    st.metric(
        label,
        value,
        delta,
        delta_color="off" if flat else "inverse" if inverse else "normal",
        delta_arrow="off" if flat else "auto",
        help=help_text,
        border=True,
        height="stretch",
        chart_data=series if len(series) > 1 and shown is not None else None,
        chart_type=chart,
        delta_description=note,
    )


def _year_ago(
    history: Sequence[FinancialPeriod], getter: Getter
) -> tuple[float, float, FinancialPeriod] | None:
    if not history:
        return None
    latest = history[-1]
    prior = comparable_period(history[:-1], latest)
    if prior is None:
        return None
    current, previous = getter(latest), getter(prior)
    if current is None or previous is None:
        return None
    return current, previous, prior


def _latest_period(bundle: AnalysisBundle) -> FinancialPeriod | None:
    if not bundle.statements.data:
        return None
    return max(bundle.statements.data, key=lambda row: row.period_ending)


def price_window(points: list[PricePoint], window: str) -> list[PricePoint]:
    """Filter calendar-day windows relative to the latest available observation."""
    ordered = sorted(points, key=lambda point: _price_date(point))
    days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}.get(window)
    if not ordered or days is None:
        return ordered
    start = _price_date(ordered[-1]) - timedelta(days=days)
    return [point for point in ordered if _price_date(point) >= start]


def _price_date(point: PricePoint) -> date:
    return point.date.date() if isinstance(point.date, datetime) else point.date


@st.fragment
def render_price_history(bundle: AnalysisBundle) -> None:
    """Range changes rerun this chart only and never fetch provider data."""
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("**Price history**")
        st.space("stretch")
        window = st.segmented_control(
            "Price range",
            ["1M", "3M", "6M", "1Y", "All"],
            default="1Y",
            key=f"price-range-{bundle.symbol}",
            label_visibility="collapsed",
        )
    points = price_window(bundle.prices.data, window or "1Y")
    if points:
        first, last = points[0], points[-1]
        change = last.close / first.close - 1 if first.close > 0 and len(points) > 1 else None
        prefix = kit.currency_prefix(bundle.prices.currency or bundle.profile.data.currency)
        closes = [point.close for point in points]
        volumes = [point.volume for point in points if point.volume is not None]
        tone = "" if change is None else "up" if change > 0 else "down" if change < 0 else ""
        st.html(
            kit.stat_strip(
                [
                    (
                        f"Change · {window or '1Y'}",
                        f"{change:+.2%}" if change is not None else "—",
                        tone,
                    ),
                    ("Range high", f"{prefix}{max(closes):,.2f}", ""),
                    ("Range low", f"{prefix}{min(closes):,.2f}", ""),
                    (
                        "Avg. volume",
                        f"{sum(volumes) / len(volumes):,.0f}" if volumes else "—",
                        "",
                    ),
                ],
                compact=True,
            )
        )
        st.caption(
            f"{_price_date(first):%d %b %Y} – {_price_date(last):%d %b %Y} · "
            "Historical close; excludes dividends. Ranges end at the latest available observation."
        )
    st.plotly_chart(
        price_figure(points, symbol=bundle.symbol),
        width="stretch",
        config={"displaylogo": False, "responsive": True, "displayModeBar": False},
        key=f"price-{bundle.symbol}",
    )
    st.caption(_dataset_caption(bundle.prices))


def render_data_health(bundle: AnalysisBundle) -> None:
    """Expose freshness, coverage, provider, and warnings for every dataset."""

    datasets: list[tuple[str, DatasetResult[Any]]] = [
        ("Profile", bundle.profile),
        ("Prices", bundle.prices),
        ("Statements", bundle.statements),
        ("Metrics", bundle.metrics),
    ]
    with st.expander("Data health", icon=":material/health_and_safety:"):
        rows = []
        for label, result in datasets:
            warnings = " · ".join(result.warnings)
            rows.append(
                {
                    "Dataset": label,
                    "Status": _dataset_status(result),
                    "Provider": result.provider,
                    "Source date": _format_date(result.as_of),
                    "Retrieved": result.retrieved_at.replace(
                        tzinfo=result.retrieved_at.tzinfo or UTC
                    )
                    .astimezone(UTC)
                    .strftime("%d %b %Y, %H:%M UTC"),
                    "Coverage": result.coverage,
                    "Notes": warnings or "No provider warnings",
                }
            )
        frame = pd.DataFrame(rows)
        st.dataframe(
            frame,
            hide_index=True,
            column_config={
                "Dataset": st.column_config.TextColumn("Dataset", pinned=True),
                "Coverage": st.column_config.ProgressColumn(
                    "Coverage", min_value=0.0, max_value=1.0, format="percent"
                ),
            },
            key=f"health-{bundle.symbol}",
        )


def _dataset_status(result: DatasetResult[Any]) -> str:
    status = "Stale" if result.stale else "Available"
    if not result.coverage:
        status = "Unavailable"
    elif not result.stale and result.coverage < 1:
        status = "Partial"
    elif not result.stale and result.as_of is None:
        status = "Source date unknown"
    return status


def _dataset_caption(result: DatasetResult[Any]) -> str:
    return f"{result.provider} · source {_format_date(result.as_of)}"


def _format_date(value: date | datetime | None) -> str:
    if value is None:
        return "Unavailable"
    return value.strftime("%d %b %Y")


def _format_score(value: int | None) -> str:
    return f"{value}/100" if value is not None else "—"


def _format_percent(value: float | None) -> str:
    return f"{value:.1%}" if value is not None else "—"


def _format_multiple(value: float | None) -> str:
    return f"{value:.2f}×" if value is not None else "—"


def _format_pe(value: float | None, *, derived: bool) -> str:
    text = _format_multiple(value)
    return f"≈ {text}" if derived and value is not None else text


def format_compact_money(value: float | None, currency: str | None = "INR") -> str:
    """Card-width INR: lakh crore at or above ₹1,00,000 Cr, otherwise whole crore."""
    if value is not None and currency == "INR" and abs(value) >= 1e12:
        return f"₹ {value / 1e12:,.2f} L Cr"
    return _format_money(value, currency)


def _format_money(value: float | None, currency: str | None = "INR") -> str:
    if value is None:
        return "—"
    if currency == "INR":
        return f"₹ {value / 10_000_000:,.0f} Cr"
    return f"{currency or 'Currency unknown'} {value:,.0f}"
