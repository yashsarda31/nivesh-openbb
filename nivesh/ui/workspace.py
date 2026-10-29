"""Research home and navigation, backed only by the current user's session."""

from __future__ import annotations

import streamlit as st

from nivesh.domain.models import AnalysisBundle

RELEASE = "Workspace 2.0"


def queue_company(symbol: str) -> None:
    """Queue a provider request; callbacks run before the search widgets render."""
    st.session_state.ticker_input = symbol
    st.session_state.pending_symbol = symbol


def open_recent(symbol: str) -> None:
    """Restore a loaded snapshot without a network request or losing notes."""
    bundle = st.session_state.analysis_bundles[symbol]
    st.session_state.current_bundle = bundle
    st.session_state.active_symbol = symbol
    st.session_state.ticker_input = symbol
    st.session_state.frequency = (
        "Quarterly" if bundle.statements.period in {"quarter", "quarterly"} else "Annual"
    )
    st.session_state.workspace_view = "Overview"
    st.session_state.show_home = False
    st.session_state.analysis_error = None


def _navigate(view: str) -> None:
    st.session_state.show_home = view == "Home"
    if view != "Home":
        st.session_state.workspace_view = view


def render_sidebar() -> None:
    bundle = st.session_state.current_bundle
    has_company = isinstance(bundle, AnalysisBundle)
    with st.sidebar:
        st.title("Nivesh", icon=":material/query_stats:")
        st.caption("THE FUNDAMENTAL EDGE")
        st.space("small")
        st.caption("WORKSPACE")
        home = st.session_state.show_home or not has_company
        st.button(
            "Research home",
            key="research-home",
            icon=":material/grid_view:",
            type="primary" if home else "tertiary",
            width="stretch",
            on_click=_navigate,
            args=("Home",),
        )
        st.button(
            "Company research",
            key="company-workspace",
            icon=":material/analytics:",
            type="tertiary",
            width="stretch",
            disabled=not has_company,
            on_click=_navigate,
            args=("Overview",),
        )
        st.button(
            f"Compare companies · {len(st.session_state.compare_symbols)}/4",
            key="compare-workspace",
            icon=":material/compare_arrows:",
            type="tertiary",
            width="stretch",
            disabled=not has_company,
            on_click=_navigate,
            args=("Compare",),
        )
        st.button(
            "Research notebook",
            key="notebook-workspace",
            icon=":material/edit_note:",
            type="tertiary",
            width="stretch",
            disabled=not has_company,
            on_click=_navigate,
            args=("Notebook",),
        )
        st.space("small")
        st.caption("RECENT RESEARCH")
        recent = list(st.session_state.analysis_bundles.items())[-6:]
        if not recent:
            st.caption("Your researched companies will appear here.")
        for symbol, saved in reversed(recent):
            frequency = "Q" if saved.statements.period in {"quarter", "quarterly"} else "FY"
            st.button(
                f"{symbol} · {frequency}",
                key=f"recent-{symbol}",
                icon=":material/history:",
                type="tertiary",
                width="stretch",
                on_click=open_recent,
                args=(symbol,),
            )
        st.space("medium")
        with st.container(border=True):
            st.markdown("**Built for the research process.**")
            st.caption("Company evidence, comparable financials, and your own investment thesis.")
        st.caption(f"{RELEASE} · Powered by OpenBB")
        st.caption("Public access · Session-only workspace")


def render_home(demo_mode: bool) -> None:
    st.space("small")
    left, right = st.columns([1.65, 1], gap="large", vertical_alignment="center")
    with left:
        st.badge("INDIA EQUITY RESEARCH", icon=":material/travel_explore:", color="green")
        st.title("Know the business.")
        st.subheader("Build your conviction.")
        st.write(
            "A focused workspace for understanding Indian companies. "
            "Connect financial performance, valuation, and the evidence behind your thesis."
        )
        st.caption("NSE & BSE coverage · Annual & quarterly statements · Source-aware research")
    with right, st.container(border=True):
        st.caption("YOUR RESEARCH WORKFLOW")
        st.markdown("### One company. The full picture.")
        st.markdown(
            ":material/search: **Understand**  \nExplore the business and its financial history."
        )
        st.markdown(
            ":material/fact_check: **Evaluate**  \nWeigh sourced strengths, risks, and data gaps."
        )
        st.markdown(
            ":material/edit_note: **Develop**  \nWrite your thesis and export your research."
        )

    st.space("small")
    st.subheader("Start your next deep dive")
    st.caption(
        "Quick-start companies, not investment recommendations. Select one to fetch its data."
    )
    examples = [
        ("RELIANCE", "Reliance Industries", "Energy & consumer businesses", "corporate_fare"),
        ("TCS", "Tata Consultancy Services", "IT services & consulting", "terminal"),
    ]
    if not demo_mode:
        examples.append(
            ("HDFCBANK", "HDFC Bank", "Banking & financial services", "account_balance")
        )
    for column, (symbol, name, description, icon) in zip(
        st.columns(len(examples)), examples, strict=True
    ):
        with column, st.container(border=True, height="stretch"):
            st.markdown(f":material/{icon}: **{symbol}**")
            st.markdown(name)
            st.caption(description)
            st.space("stretch")
            st.button(
                f"Research {symbol}",
                key=f"quick-{symbol}",
                icon=":material/arrow_forward:",
                width="stretch",
                on_click=queue_company,
                args=(symbol,),
            )
    with st.expander("How Nivesh handles your research", icon=":material/info:"):
        st.write(
            "Financial data comes from the configured provider through OpenBB. Source dates, "
            "coverage, and missing inputs remain visible. Scores organize research; they are "
            "not buy or sell recommendations. Recent companies and saved notes stay in this "
            "browser session only. Download your work before closing or reloading the app."
        )
