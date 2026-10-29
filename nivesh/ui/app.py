"""Public Streamlit orchestration for the Nivesh analyst workspace."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Literal

import streamlit as st

from nivesh.config import AppSettings
from nivesh.domain.models import AnalysisBundle
from nivesh.services.analysis import (
    DemoSymbolUnavailableError,
    load_demo_analysis,
)
from nivesh.services.loaders import (
    bump_refresh_nonce,
    configure_openbb_credentials,
    load_analysis,
)
from nivesh.services.tickers import SymbolValidationError, resolve_symbol
from nivesh.ui import kit
from nivesh.ui.comparison import render_compare_action, render_comparison
from nivesh.ui.financials import render_financials
from nivesh.ui.notebook import render_notebook
from nivesh.ui.overview import render_company_header, render_overview
from nivesh.ui.scores import render_scores
from nivesh.ui.styles import apply_styles
from nivesh.ui.workspace import RELEASE, render_hero_copy, render_home, render_sidebar

_VIEW_ICONS = {
    "Overview": ":material/dashboard:",
    "Financials": ":material/bar_chart:",
    "Score": ":material/speed:",
    "Compare": ":material/compare_arrows:",
    "Notebook": ":material/edit_note:",
}


def run_app() -> None:
    """Render the complete public, no-login analysis workflow."""

    settings = AppSettings.from_mapping(os.environ)
    _initialize_state()
    apply_styles()
    render_sidebar()

    bundle = st.session_state.get("current_bundle")
    home = not isinstance(bundle, AnalysisBundle) or st.session_state.show_home
    _render_topbar(None if home or not isinstance(bundle, AnalysisBundle) else bundle, settings)

    if settings.demo_mode:
        st.info(
            "Demo data · not a live provider result. Available examples: RELIANCE and TCS.",
            icon=":material/science:",
        )

    if home:
        with st.container(key="home-hero"):
            render_hero_copy()
            submitted, ticker, frequency = _render_search_form(compact=False)
    else:
        submitted, ticker, frequency = _render_search_form(compact=True)
    pending = st.session_state.pop("pending_symbol", None)
    if submitted or pending:
        _handle_analysis(pending or ticker, frequency, settings)
        st.rerun()

    error = st.session_state.get("analysis_error")
    if error:
        st.error(error, icon=":material/error:")

    if home or not isinstance(bundle, AnalysisBundle):
        render_home(settings.demo_mode)
        st.html(kit.footer(_source_label(settings), RELEASE))
        return

    render_company_header(bundle, actions=lambda: _render_actions(bundle, settings))
    st.space("small")
    view = st.segmented_control(
        "Workspace",
        list(_VIEW_ICONS),
        format_func=lambda option: f"{_VIEW_ICONS[option]} {option}",
        key="workspace_view",
        label_visibility="collapsed",
        persist_state="session",
        width="stretch",
    )
    st.space("small")
    if view == "Compare":
        bundles_by_symbol = st.session_state.get("analysis_bundles", {})
        render_comparison(bundles_by_symbol, st.session_state.compare_symbols)
    elif view == "Financials":
        render_financials(bundle)
    elif view == "Score":
        render_scores(bundle)
    elif view == "Notebook":
        render_notebook(bundle)
    else:
        render_overview(bundle)
    st.html(kit.footer(_source_label(settings), RELEASE))


def _source_label(settings: AppSettings) -> str:
    return "demo fixtures" if settings.demo_mode else settings.provider


def _render_topbar(bundle: AnalysisBundle | None, settings: AppSettings) -> None:
    crumbs = ["RESEARCH DESK", "India equities"]
    if bundle is not None:
        period = (bundle.statements.period or "annual").casefold()
        crumbs.append(
            "Quarterly statements" if period in {"quarter", "quarterly"} else "Annual statements"
        )
    pills = [
        ("Demo data", "warn")
        if settings.demo_mode
        else (f"Data: {settings.provider} via OpenBB", "info"),
        ("Public workspace", "muted"),
    ]
    st.html(kit.topbar(crumbs, pills, code=bundle.symbol if bundle else None))


def _render_actions(bundle: AnalysisBundle, settings: AppSettings) -> None:
    render_compare_action(bundle)
    if st.button(
        "Refresh data",
        key="refresh-current",
        icon=":material/refresh:",
        type="tertiary",
    ):
        _refresh_current(bundle, settings)
        st.rerun()


def _initialize_state() -> None:
    st.session_state.setdefault("active_symbol", None)
    st.session_state.setdefault("compare_symbols", [])
    st.session_state.setdefault("frequency", "Annual")
    st.session_state.setdefault("refresh_nonces", {})
    st.session_state.setdefault("analysis_error", None)
    st.session_state.setdefault("current_bundle", None)
    st.session_state.setdefault("analysis_bundles", {})
    st.session_state.setdefault("workspace_view", "Overview")
    st.session_state.setdefault("show_home", True)
    st.session_state.setdefault("research_notes", {})


def _render_search_form(*, compact: bool) -> tuple[bool, str, str]:
    """Ticker search; compact mode keeps the labels for assistive technology only."""
    labels: Literal["visible", "collapsed"] = "collapsed" if compact else "visible"
    with st.container(
        key="command-bar",
        horizontal=True,
        vertical_alignment="bottom",
        gap="medium",
    ):
        with (
            st.form("ticker_search", border=False, width=600),
            st.container(horizontal=True, vertical_alignment="bottom", gap="small"),
        ):
            ticker = st.text_input(
                "NSE or BSE ticker",
                key="ticker_input",
                placeholder="RELIANCE, TCS.NS or 500325.BO",
                max_chars=30,
                persist_state="session",
                icon=":material/search:",
                label_visibility=labels,
            )
            submitted = st.form_submit_button(
                "Analyze",
                key="analyze_button",
                type="primary",
                icon=":material/arrow_forward:",
                icon_position="right",
            )
        frequency = st.segmented_control(
            "Reporting frequency",
            ["Annual", "Quarterly"],
            key="frequency",
            persist_state="session",
            width=210,
            wrap=True,
            label_visibility=labels,
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
        with st.spinner(
            f"Assembling {resolved.symbol}: prices, statements and metrics from {source}…",
            show_time=True,
        ):
            bundle = _load_bundle(resolved.symbol, period, settings)
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
    bundles = dict(st.session_state.analysis_bundles)
    bundles.pop(resolved.symbol, None)
    bundles[resolved.symbol] = bundle
    # Bound retained financial snapshots; comparison members stay available.
    while len(bundles) > 12:
        oldest = next(
            symbol
            for symbol in bundles
            if symbol not in st.session_state.compare_symbols and symbol != resolved.symbol
        )
        del bundles[oldest]
    st.session_state.analysis_bundles = bundles
    st.session_state.analysis_error = None
    st.session_state.workspace_view = "Overview"
    st.session_state.show_home = False


def _load_bundle(symbol: str, period: str, settings: AppSettings) -> AnalysisBundle:
    if settings.demo_mode:
        return load_demo_analysis(symbol, period)
    configure_openbb_credentials(_openbb_secrets())
    cache_key = f"{settings.provider}:{symbol}"
    nonce = st.session_state.refresh_nonces.get(cache_key, 0)
    return load_analysis(symbol, settings.provider, period, nonce)


def _refresh_current(bundle: AnalysisBundle, settings: AppSettings) -> None:
    provider = "demo" if settings.demo_mode else settings.provider
    st.session_state.refresh_nonces = bump_refresh_nonce(
        st.session_state.refresh_nonces,
        bundle.symbol,
        provider,
    )
    try:
        refreshed = _load_bundle(
            bundle.symbol,
            bundle.statements.period or "annual",
            settings,
        )
    except Exception as exc:
        st.session_state.analysis_error = (
            f"Refresh failed; the previous valid data remains visible: {exc}"
        )
        return
    st.session_state.current_bundle = refreshed
    saved = dict(st.session_state.analysis_bundles)
    saved[bundle.symbol] = refreshed
    st.session_state.analysis_bundles = saved
    st.session_state.analysis_error = None
    st.toast(f"Refreshed {bundle.symbol}")


def _openbb_secrets() -> Mapping[str, Any]:
    try:
        section = st.secrets.get("openbb", {})
    except Exception:
        return {}
    return section if isinstance(section, Mapping) else {}
