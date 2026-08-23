"""Public Streamlit orchestration for the Nivesh analyst workspace."""

from __future__ import annotations

import os

import streamlit as st

from nivesh.config import AppSettings
from nivesh.domain.models import AnalysisBundle
from nivesh.services.analysis import (
    DemoSymbolUnavailableError,
    fetch_live_analysis,
    load_demo_analysis,
)
from nivesh.services.tickers import SymbolValidationError, resolve_symbol
from nivesh.ui.financials import render_financials
from nivesh.ui.overview import render_overview
from nivesh.ui.scores import render_scores
from nivesh.ui.styles import apply_styles


def run_app() -> None:
    """Render the complete public, no-login analysis workflow."""

    settings = AppSettings.from_mapping(os.environ)
    _initialize_state()
    apply_styles()

    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
    ):
        st.title("Nivesh")
        st.badge("Public analyst workspace", icon=":material/public:", color="green")
    st.caption("India fundamental intelligence · OpenBB foundation · no login required")

    if settings.demo_mode:
        st.info(
            "Demo data · not a live provider result. Available examples: RELIANCE and TCS.",
            icon=":material/science:",
        )

    submitted, ticker, frequency = _render_search_form()
    if submitted:
        _handle_analysis(ticker, frequency, settings)

    error = st.session_state.get("analysis_error")
    if error:
        st.error(error, icon=":material/error:")

    bundle = st.session_state.get("current_bundle")
    if not isinstance(bundle, AnalysisBundle):
        _render_empty_state(settings.demo_mode)
        return

    st.space("small")
    view = st.segmented_control(
        "Workspace",
        ["Overview", "Financials", "Score"],
        key="workspace_view",
        label_visibility="collapsed",
        persist_state="session",
    )
    if view == "Financials":
        render_financials(bundle)
    elif view == "Score":
        render_scores(bundle)
    else:
        render_overview(bundle)


def _initialize_state() -> None:
    st.session_state.setdefault("active_symbol", None)
    st.session_state.setdefault("compare_symbols", [])
    st.session_state.setdefault("frequency", "Annual")
    st.session_state.setdefault("refresh_nonces", {})
    st.session_state.setdefault("analysis_error", None)
    st.session_state.setdefault("current_bundle", None)
    st.session_state.setdefault("workspace_view", "Overview")


def _render_search_form() -> tuple[bool, str, str]:
    with st.form("ticker_search", border=False), st.container(
        horizontal=True, vertical_alignment="bottom"
    ):
        ticker = st.text_input(
            "NSE or BSE ticker",
            key="ticker_input",
            placeholder="RELIANCE, TCS.NS or 500325.BO",
            max_chars=30,
            persist_state="session",
        )
        frequency = st.segmented_control(
            "Reporting frequency",
            ["Annual", "Quarterly"],
            key="frequency",
            persist_state="session",
        )
        submitted = st.form_submit_button(
            "Analyze",
            key="analyze_button",
            type="primary",
            icon=":material/search:",
        )
    return submitted, ticker, frequency or "Annual"


def _handle_analysis(ticker: str, frequency: str, settings: AppSettings) -> None:
    try:
        resolved = resolve_symbol(ticker)
    except SymbolValidationError as exc:
        st.session_state.analysis_error = str(exc)
        return

    period = frequency.casefold()
    try:
        source = "demo data" if settings.demo_mode else settings.provider
        with st.spinner(f"Loading {resolved.symbol} from {source}..."):
            bundle = (
                load_demo_analysis(resolved.symbol, period)
                if settings.demo_mode
                else fetch_live_analysis(resolved.symbol, period, settings.provider)
            )
    except DemoSymbolUnavailableError as exc:
        st.session_state.analysis_error = str(exc)
        return
    except Exception as exc:
        st.session_state.analysis_error = (
            f"Unable to load {resolved.symbol} from {settings.provider}: {exc}"
        )
        return

    st.session_state.active_symbol = resolved.symbol
    st.session_state.current_bundle = bundle
    st.session_state.analysis_error = None
    st.session_state.workspace_view = "Overview"


def _render_empty_state(demo_mode: bool) -> None:
    with st.container(border=True):
        st.subheader("Start with an Indian listed company")
        st.write(
            "Enter an NSE symbol or six-digit BSE code to inspect financial history, "
            "ratios, valuation and score coverage."
        )
        examples = "RELIANCE or TCS" if demo_mode else "RELIANCE, TCS.NS or 500325.BO"
        st.caption(f"Examples: {examples}")
