"""Single-company identity, key metrics, price history, and data health."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
import streamlit as st

from nivesh.domain.models import (
    AnalysisBundle,
    DatasetResult,
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
    with st.container(horizontal=True):
        st.metric("Nivesh score", _format_score(score), border=True)
        st.metric(
            "Revenue",
            _format_money(latest.revenue if latest else None, profile.currency),
            border=True,
        )
        st.metric("ROE", _format_percent(ratios.get("roe")), border=True)
        st.metric(
            "Operating margin",
            _format_percent(ratios.get("operating_margin")),
            border=True,
        )
        st.metric("P/E", _format_pe(pe_value, derived=pe_derived), border=True)
        st.metric(
            "Debt / equity",
            _format_multiple(ratios.get("debt_equity")),
            border=True,
        )

    roe_basis = (
        "TTM with average year-ago equity"
        if frequency in {"quarter", "quarterly"}
        else "annual with average equity where available"
    )
    st.caption(
        f"{frequency} · latest period {latest.period_ending if latest else 'unknown'} · "
        f"{bundle.statements.provider} · ROE basis: {roe_basis}"
    )
    render_research(bundle)
    left, right = st.columns([2, 1], vertical_alignment="top")
    with left, st.container(border=True):
        st.markdown("**Price history**")
        st.caption(_dataset_caption(bundle.prices))
        st.plotly_chart(
            price_figure(bundle.prices.data, symbol=bundle.symbol),
            width="stretch",
            config={"displaylogo": False, "responsive": True},
            key=f"price-{bundle.symbol}",
        )
    with right, st.container(border=True, height="stretch"):
        st.markdown("**Company context**")
        st.write(profile.description or "Company description unavailable from provider.")
        st.caption(
            "Industry: "
            + (profile.industry or "Unavailable")
            + "\n\nMarket cap: "
            + _format_money(profile.market_cap, profile.currency)
        )
        if profile.website:
            st.link_button(
                "Company website",
                profile.website,
                icon=":material/open_in_new:",
                type="tertiary",
            )

    render_data_health(bundle)


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
