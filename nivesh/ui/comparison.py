"""Responsive comparison tray, normalized chart, and exact-value table."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
import streamlit as st

from nivesh.components.financial_towers import render_financial_towers
from nivesh.domain.models import AnalysisBundle
from nivesh.services.comparison import build_comparison, normalized_price_frame
from nivesh.ui.charts import comparison_figure


def render_compare_action(bundle: AnalysisBundle) -> None:
    """Offer the active company to the bounded, per-session comparison tray."""

    selected = list(st.session_state.get("compare_symbols", []))
    already_added = bundle.symbol in selected
    limit_reached = len(selected) >= 4
    label = "In comparison" if already_added else f"Add {bundle.symbol} to comparison"
    if st.button(
        label,
        key="add-current-to-compare",
        icon=":material/add_chart:",
        type="tertiary",
        disabled=already_added or limit_reached,
    ):
        st.session_state.compare_symbols = [*selected, bundle.symbol]
        st.toast(f"Added {bundle.symbol} to comparison")
        st.rerun()
    if limit_reached and not already_added:
        st.caption("Comparison is limited to four companies.")


def render_comparison(
    bundles_by_symbol: Mapping[str, AnalysisBundle],
    selected_symbols: Sequence[str],
) -> None:
    """Render the exact comparison workspace for selected, already-loaded bundles."""

    st.subheader("Company comparison")
    st.caption(" · ".join(selected_symbols) if selected_symbols else "No companies selected")
    _render_tray(selected_symbols)

    bundles = [
        bundles_by_symbol[symbol] for symbol in selected_symbols if symbol in bundles_by_symbol
    ]
    if len(bundles) < 2:
        st.info(
            "Add at least two analyzed companies to compare them. The limit is four.",
            icon=":material/compare_arrows:",
        )
        return

    try:
        payload = build_comparison(bundles)
    except ValueError as exc:
        st.info(str(exc), icon=":material/compare_arrows:")
        return
    for warning in payload.warnings:
        st.warning(warning, icon=":material/warning:")

    with st.container(border=True):
        st.markdown("**Normalized price performance**")
        st.caption(
            "All series start at 100 on their first shared positive-close date. "
            "Missing observations stay missing; dividends are not added."
        )
        prices = normalized_price_frame(bundles)
        if prices.empty:
            st.info("No shared positive-close date is available for this selection.")
        else:
            st.plotly_chart(
                comparison_figure(
                    prices,
                    y_title="Indexed close (common start = 100)",
                ),
                width="stretch",
                config={"displaylogo": False, "responsive": True},
                key="comparison-price-chart",
            )

    st.markdown("**Fundamental comparison**")
    frame = pd.DataFrame(row.model_dump() for row in payload.rows)
    st.dataframe(
        frame[
            [
                "company",
                "symbol",
                "label",
                "display_value",
                "period",
                "currency",
                "provider",
                "warning",
            ]
        ],
        hide_index=True,
        key="comparison-table",
        column_config={
            "company": st.column_config.TextColumn("Company", pinned=True),
            "symbol": st.column_config.TextColumn("Symbol"),
            "label": st.column_config.TextColumn("Metric"),
            "display_value": st.column_config.TextColumn("Value"),
            "period": st.column_config.TextColumn("Period"),
            "currency": st.column_config.TextColumn("Currency"),
            "provider": st.column_config.TextColumn("Provider"),
            "warning": st.column_config.TextColumn("Data note"),
        },
    )

    st.markdown("**Interactive score towers**")
    st.caption("Tower height follows the selected score. Exact values remain in the table above.")
    render_financial_towers(
        [tower.model_dump() for tower in payload.towers],
        key="financial-towers",
    )


def _render_tray(selected_symbols: Sequence[str]) -> None:
    if not selected_symbols:
        return
    with st.container(horizontal=True, vertical_alignment="center"):
        for symbol in selected_symbols:
            if st.button(
                f"Remove {symbol}",
                key=f"remove-compare-{symbol}",
                icon=":material/close:",
                type="tertiary",
            ):
                st.session_state.compare_symbols = [
                    item for item in selected_symbols if item != symbol
                ]
                st.rerun()
