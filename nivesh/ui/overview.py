"""Single-company identity, key metrics, price history, and data health."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from nivesh.domain.models import (
    AnalysisBundle,
    DatasetResult,
    PricePoint,
)
from nivesh.services.fundamentals import ALIASES, fundamental_inputs
from nivesh.ui.charts import price_figure
from nivesh.ui.research import render_research


def render_overview(bundle: AnalysisBundle) -> None:
    """Render the analyst overview without hiding unavailable values."""

    profile = bundle.profile.data
    title = profile.name or bundle.symbol
    st.subheader(title)
    identity = " · ".join(
        value for value in (bundle.symbol, profile.exchange, profile.sector) if value
    )
    st.caption(identity)
    st.caption("Research support, not a recommendation. Review coverage and source dates.")

    latest = (
        max(bundle.statements.data, key=lambda row: row.period_ending)
        if bundle.statements.data
        else None
    )
    frequency = bundle.statements.period or "annual"
    ratios = fundamental_inputs(
        bundle.statements.data, bundle.metrics.data, frequency, profile.market_cap
    )
    provider_metrics = bundle.metrics.data
    score = bundle.scorecard.composite if bundle.scorecard else None

    pe_value = ratios.get("pe_ratio")
    pe_derived = (
        not any(provider_metrics.get(key) is not None for key in ALIASES["pe_ratio"])
        and pe_value is not None
    )
    if pe_value is not None and pe_value <= 0:
        pe_value = None
    cards = [
        (
            "Nivesh score",
            _format_score(score),
            "A research score, not a recommendation. Review input coverage in Score.",
        ),
        (
            "Revenue",
            _format_money(latest.revenue if latest else None, profile.currency),
            f"Revenue for the latest reported {frequency} period; not necessarily TTM.",
        ),
        ("ROE", _format_percent(ratios.get("roe")), "Return on equity; see the basis below."),
        (
            "Operating margin",
            _format_percent(ratios.get("operating_margin")),
            "Operating income divided by revenue for the reported period.",
        ),
        (
            "P/E",
            _format_pe(pe_value, derived=pe_derived),
            "Provider multiple, or a statement-derived estimate marked with ≈.",
        ),
        (
            "Debt / equity",
            _format_multiple(ratios.get("debt_equity")),
            "Total debt relative to equity; not a bank capital-adequacy measure.",
        ),
    ]
    for start in (0, 3):
        for column, (label, value, help_text) in zip(
            st.columns(3), cards[start : start + 3], strict=True
        ):
            column.metric(label, value, help=help_text, border=True)

    roe_basis = (
        "TTM with average year-ago equity"
        if frequency in {"quarter", "quarterly"}
        else "annual with average equity where available"
    )
    st.caption(
        f"{frequency} · latest period {latest.period_ending if latest else 'unknown'} · "
        f"{bundle.statements.provider} · ROE basis: {roe_basis}"
    )
    left, right = st.columns([2, 1], vertical_alignment="top")
    with left, st.container(border=True):
        render_price_history(bundle)
    with right, st.container(border=True, height="stretch"):
        st.markdown("**Research readiness**")
        datasets = (bundle.profile, bundle.prices, bundle.statements, bundle.metrics)
        if any(ds.stale for ds in datasets):
            st.badge("Older source records", icon=":material/schedule:", color="orange")
        elif any(ds.coverage < 1 or ds.as_of is None for ds in datasets):
            st.badge("Review data gaps", icon=":material/info:", color="orange")
        else:
            st.badge("Source dates available", icon=":material/fact_check:", color="green")
        if bundle.scorecard:
            st.progress(
                bundle.scorecard.coverage,
                text=f"{bundle.scorecard.coverage:.0%} score input coverage",
            )
        st.caption("Coverage measures available inputs, not confidence or investment quality.")
        st.markdown("**Company context**")
        st.caption(
            "Industry: "
            + (profile.industry or "Unavailable")
            + "\n\nMarket cap: "
            + _format_money(profile.market_cap, profile.currency)
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

    render_data_health(bundle)
    render_research(bundle)


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
    st.markdown("**Price history**")
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
        currency = bundle.prices.currency or bundle.profile.data.currency or ""
        change_text = (
            f"{change:+.2%} over selected observations"
            if change is not None
            else "Change unavailable"
        )
        st.markdown(f"**{currency} {last.close:,.2f}** · {change_text}")
        st.caption(
            f"{_price_date(first):%d %b %Y} – {_price_date(last):%d %b %Y} · "
            "Historical close; excludes dividends. Ranges end at the latest available observation."
        )
    st.caption(_dataset_caption(bundle.prices))
    st.plotly_chart(
        price_figure(points, symbol=bundle.symbol),
        width="stretch",
        config={"displaylogo": False, "responsive": True},
        key=f"price-{bundle.symbol}",
    )


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
            status = "Stale" if result.stale else "Available"
            if not result.coverage:
                status = "Unavailable"
            elif not result.stale and result.coverage < 1:
                status = "Partial"
            elif not result.stale and result.as_of is None:
                status = "Source date unknown"
            rows.append(
                {
                    "Dataset": label,
                    "Status": status,
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


def _format_money(value: float | None, currency: str | None = "INR") -> str:
    if value is None:
        return "—"
    if currency == "INR":
        return f"₹ {value / 10_000_000:,.0f} Cr"
    return f"{currency or 'Currency unknown'} {value:,.0f}"
