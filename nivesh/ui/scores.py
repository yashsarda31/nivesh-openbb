"""Coverage-aware score cards and inspectable methodology details."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from nivesh.domain.models import AnalysisBundle

_COMPONENT_LABELS = {
    "quality": "Quality",
    "growth": "Growth",
    "balance": "Balance sheet",
    "valuation": "Valuation",
}


def render_scores(bundle: AnalysisBundle) -> None:
    """Render the score as research support with all exclusions visible."""

    scorecard = bundle.scorecard
    st.subheader("Fundamental score")
    st.caption("Research support, not a recommendation. Methodology version nivesh-v1.")
    if scorecard is None:
        st.warning("Score unavailable because no normalized financial inputs were returned.")
        return

    with st.container(horizontal=True):
        st.metric(
            "Composite",
            f"{scorecard.composite}/100" if scorecard.composite is not None else "—",
            f"{scorecard.coverage:.0%} input coverage",
            delta_color="off",
            border=True,
        )
        for name, component in scorecard.components.items():
            st.metric(
                _COMPONENT_LABELS.get(name, name.title()),
                f"{component.score}/100" if component.score is not None else "—",
                f"{component.coverage:.0%} coverage",
                delta_color="off",
                border=True,
            )

    for warning in scorecard.warnings:
        st.warning(warning, icon=":material/warning:")

    with st.expander("Scoring methodology", icon=":material/function:"):
        rows = []
        for component_name, component in scorecard.components.items():
            for metric in component.metrics.values():
                rows.append(
                    {
                        "Component": _COMPONENT_LABELS.get(component_name, component_name.title()),
                        "Metric": metric.label,
                        "Raw value": metric.raw_value,
                        "Score": metric.score,
                        "Effective weight": metric.effective_weight,
                        "Direction": metric.direction,
                        "Source period": metric.source_period or "—",
                        "Exclusion": metric.excluded_reason or "—",
                    }
                )
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            key=f"methodology-{bundle.symbol}",
            column_config={
                "Component": st.column_config.TextColumn("Component", pinned=True),
                "Effective weight": st.column_config.NumberColumn(
                    "Effective weight", format="percent"
                ),
            },
        )
        st.caption(
            "Scores use documented fixed bands. Missing metrics are excluded, never scored as zero."
        )
