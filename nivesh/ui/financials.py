"""Financial statement trend workspace with exact-value alternatives."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st

from nivesh.domain.models import AnalysisBundle, FinancialPeriod
from nivesh.services.normalization import enrich_periods
from nivesh.ui import kit
from nivesh.ui.charts import financial_trend_figure, margin_figure
from nivesh.ui.overview import format_compact_money, metric_card


def render_financials(bundle: AnalysisBundle) -> None:
    """Render aligned income, cash flow, margin, and balance-sheet history."""

    periods = bundle.statements.data
    frame = _statement_frame(bundle)
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container(gap=None):
            st.subheader("Financial history", anchor=False)
            st.caption(
                f"{bundle.statements.period or 'Reported'} periods · "
                f"{bundle.statements.provider} · exact values in reported currency"
            )
        st.download_button(
            "Download financials CSV",
            data=frame.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{bundle.symbol}-{bundle.statements.period}-financials.csv",
            mime="text/csv",
            icon=":material/download:",
            key=f"financials-download-{bundle.symbol}",
            on_click="ignore",
        )

    frequency = bundle.statements.period or "annual"
    history = enrich_periods(periods, frequency)
    latest = history[-1] if history else None
    currency = bundle.statements.currency or bundle.profile.data.currency
    cards: list[tuple[str, float | None, Callable[[FinancialPeriod], float | None], str]] = [
        ("Revenue", latest.revenue if latest else None, lambda row: row.revenue, "money"),
        ("Net income", latest.net_income if latest else None, lambda row: row.net_income, "money"),
        (
            "Free cash flow",
            latest.free_cash_flow if latest else None,
            lambda row: row.free_cash_flow,
            "money",
        ),
        ("Diluted EPS", latest.diluted_eps if latest else None, lambda row: row.diluted_eps, "eps"),
    ]
    kpi_row = st.container(key="fin-kpis", horizontal=True, gap="small")
    for label, value, getter, unit in cards:
        with kpi_row:
            shown = (
                format_compact_money(value, currency)
                if unit == "money"
                else f"{kit.currency_prefix(currency)}{value:,.2f}"
                if value is not None
                else "—"
            )
            metric_card(
                label,
                shown,
                f"Latest reported {frequency} period"
                + (f" ending {latest.period_ending:%d %b %Y}." if latest else ".")
                + (
                    " Operating cash flow less capital expenditure when not reported."
                    if label == "Free cash flow"
                    else ""
                ),
                history,
                getter,
                shown=value,
                kind="growth",
            )

    with st.container(key="card-fin-income"):
        st.markdown("**Income and cash generation**")
        st.plotly_chart(
            financial_trend_figure(
                periods,
                ["revenue", "operating_income", "net_income", "free_cash_flow"],
            ),
            width="stretch",
            config={"displaylogo": False, "responsive": True, "displayModeBar": False},
            key=f"financial-trend-{bundle.symbol}",
        )

    left, right = st.columns(2)
    with left, st.container(key="card-fin-margins", height="stretch"):
        st.markdown("**Margins and returns**")
        st.plotly_chart(
            margin_figure(periods, ["operating_margin", "net_margin", "roe", "roa"]),
            width="stretch",
            config={"displaylogo": False, "responsive": True, "displayModeBar": False},
            key=f"margin-trend-{bundle.symbol}",
        )
    with right, st.container(key="card-fin-balance", height="stretch"):
        st.markdown("**Balance-sheet trend**")
        st.plotly_chart(
            financial_trend_figure(
                periods,
                ["total_equity", "total_debt", "cash"],
            ),
            width="stretch",
            config={"displaylogo": False, "responsive": True, "displayModeBar": False},
            key=f"balance-trend-{bundle.symbol}",
        )

    with st.expander("Exact reported values", icon=":material/table_chart:"):
        st.dataframe(
            frame,
            hide_index=True,
            key=f"statements-{bundle.symbol}",
            column_config={"Period": st.column_config.TextColumn("Period", pinned=True)},
        )


def _statement_frame(bundle: AnalysisBundle) -> pd.DataFrame:
    rows = []
    for period in reversed(bundle.statements.data):
        fiscal_year = period.fiscal_year or period.period_ending.year
        rows.append(
            {
                "Period": f"{period.fiscal_period or ''} {fiscal_year}".strip(),
                "Period ending": period.period_ending,
                "Revenue": period.revenue,
                "Operating profit": period.operating_income,
                "Net income": period.net_income,
                "Free cash flow": period.free_cash_flow,
                "Operating cash flow": period.operating_cash_flow,
                "Capital expenditure": period.capital_expenditure,
                "Diluted EPS": period.diluted_eps,
                "Total assets": period.total_assets,
                "Total equity": period.total_equity,
                "Total debt": period.total_debt,
                "Cash": period.cash,
                "Currency": period.currency or bundle.statements.currency or "—",
                "Frequency": bundle.statements.period,
                "Provider": bundle.statements.provider,
                "Source date": bundle.statements.as_of,
                "Retrieved UTC": bundle.statements.retrieved_at.isoformat(),
            }
        )
    return pd.DataFrame(rows)
