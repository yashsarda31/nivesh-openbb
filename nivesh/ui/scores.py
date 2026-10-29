"""Coverage-aware score cards and inspectable methodology details."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from nivesh.domain.models import AnalysisBundle
from nivesh.ui import kit

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

    left, right = st.columns([1, 2], vertical_alignment="top")
    with left, st.container(key="card-score-ring", height="stretch"):
        st.markdown("**Composite**")
        with st.container(horizontal_alignment="center"):
            st.html(
                kit.score_ring(scorecard.composite, size=168),
                width="content",
            )
        st.html(
            kit.key_values(
                [
                    ("Input coverage", f"{scorecard.coverage:.0%}"),
                    (
                        "Eligible pillars",
                        f"{sum(c.score is not None for c in scorecard.components.values())}"
                        f" of {len(scorecard.components)}",
                    ),
                    ("Methodology", scorecard.methodology_version),
                ]
            )
        )
        st.caption("Withheld when fewer than three pillars or 60% input coverage are available.")
    with right, st.container(key="card-score-pillars", height="stretch"):
        st.markdown("**Pillars**")
        st.caption(
            "Missing inputs are excluded and weights rescale within the pillar; "
            "they are never scored as zero."
        )
        st.html(
            kit.component_bars(
                [
                    (
                        _COMPONENT_LABELS.get(name, name.title()),
                        component.score,
                        component.coverage,
                        f"{len(component.metrics) - len(component.excluded)} of "
                        f"{len(component.metrics)} inputs · "
                        f"{component.target_weight:.0%} target weight",
                    )
                    for name, component in scorecard.components.items()
                ]
            )
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
