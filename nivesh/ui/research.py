"""Native research summary and same-source export."""

import streamlit as st

from nivesh.domain.models import AnalysisBundle
from nivesh.services.research import CHECKS, METHODOLOGY, build_research_brief, research_markdown


def render_research(bundle: AnalysisBundle) -> None:
    brief = build_research_brief(bundle)
    st.subheader("Research brief", icon=":material/fact_check:")
    st.caption(
        "A balanced view of the business. "
        "Every observation includes its reporting period and source."
    )
    if any(ds.stale for ds in (bundle.profile, bundle.prices, bundle.statements, bundle.metrics)):
        st.warning(
            "Stale data: research reflects older source records. Verify current filings before use."
        )
    if any("DEMO" in item for item in brief.limitations):
        st.info("DEMO DATA: illustrative research; not live company evidence.")
    for column, title, items in zip(
        st.columns(2), ("Pros", "Cons"), (brief.pros, brief.cons), strict=True
    ):
        with column, st.container(border=True, height="stretch"):
            st.markdown(f"**{title}**")
            st.caption("Demonstrated strengths" if title == "Pros" else "Demonstrated weaknesses")
            for item in items[:5]:
                st.markdown(f"**{item.title}** — {item.evidence}")
                st.caption(f"{item.period} · {item.source}")
            if len(items) > 5:
                with st.expander("Additional observations"):
                    for item in items[5:]:
                        st.markdown(f"**{item.title}** — {item.evidence}")
                        st.caption(f"{item.period} · {item.source}")
            if not items:
                st.write("No evidence-backed observations available.")
    with st.expander("Recent financial changes and valuation context", expanded=False):
        for item in brief.changes + brief.valuation_context:
            st.markdown(f"**{item.title}** — {item.evidence}")
            st.caption(f"{item.period} · {item.source}")
    with st.expander("Data limitations and research checklist", expanded=False):
        for limitation in brief.limitations:
            st.write("• " + limitation)
        st.write(CHECKS)
        st.caption(METHODOLOGY)
    latest = (
        max(bundle.statements.data, key=lambda row: row.period_ending)
        if bundle.statements.data
        else None
    )
    asof = latest.period_ending.isoformat() if latest else "unknown"
    frequency = bundle.statements.period or "annual"
    st.download_button(
        "Download research brief (Markdown)",
        research_markdown(bundle, brief),
        file_name=f"{bundle.symbol}-{frequency}-{asof}-research.md",
        mime="text/markdown",
        on_click="ignore",
        key=f"research-download-{bundle.symbol}",
        icon=":material/download:",
    )
