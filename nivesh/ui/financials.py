"""Financial statement trend workspace with exact-value alternatives."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from nivesh.domain.models import AnalysisBundle
from nivesh.ui.charts import financial_trend_figure, margin_figure


def render_financials(bundle: AnalysisBundle) -> None:
    """Render aligned income, cash flow, margin, and balance-sheet history."""

    periods = bundle.statements.data
    st.subheader("Financial history")
    st.caption(
        f"{bundle.statements.period or 'Reported'} periods · "
        f"{bundle.statements.provider} · exact values in reported currency"
    )

    with st.container(border=True):
        st.markdown("**Income and cash generation**")
        st.plotly_chart(
            financial_trend_figure(
                periods,
                ["revenue", "operating_income", "net_income", "free_cash_flow"],
            ),
            width="stretch",
            config={"displaylogo": False, "responsive": True},
            key=f"financial-trend-{bundle.symbol}",
        )

    left, right = st.columns(2)
    with left, st.container(border=True, height="stretch"):
        st.markdown("**Margins and returns**")
        st.plotly_chart(
            margin_figure(periods, ["operating_margin", "net_margin", "roe", "roa"]),
            width="stretch",
            config={"displaylogo": False, "responsive": True},
            key=f"margin-trend-{bundle.symbol}",
        )
    with right, st.container(border=True, height="stretch"):
        st.markdown("**Balance-sheet trend**")
        st.plotly_chart(
            financial_trend_figure(
                periods,
                ["total_equity", "total_debt", "cash"],
            ),
            width="stretch",
            config={"displaylogo": False, "responsive": True},
            key=f"balance-trend-{bundle.symbol}",
        )

    with st.expander("Exact reported values", icon=":material/table_chart:"):
        st.dataframe(
            _statement_frame(bundle),
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
                "Total equity": period.total_equity,
                "Total debt": period.total_debt,
                "Currency": period.currency or bundle.statements.currency or "—",
            }
        )
    return pd.DataFrame(rows)
