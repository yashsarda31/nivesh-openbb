"""Research home and navigation, backed only by the current user's session."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path

import streamlit as st

from nivesh.domain.models import AnalysisBundle
from nivesh.ui import kit

RELEASE = "Workspace 3.0"
_CATALOG = Path(__file__).parents[1] / "assets" / "india_symbols.csv"
_SCORE_PILLARS = 4
_FEATURES = (
    (
        "shield",
        "Evidence, not opinions",
        "Every strength and weakness cites its numbers, reporting period and provider.",
    ),
    (
        "gauge",
        "Transparent scoring",
        "Quality, growth, balance sheet and valuation, with each input, weight and "
        "exclusion visible.",
    ),
    (
        "calendar",
        "Annual & quarterly",
        "Normalized statements aligned on exact reporting dates; missing values stay missing.",
    ),
    (
        "bars",
        "Side-by-side comparison",
        "Index up to four companies to a common start and inspect them in 3D or exact tables.",
    ),
    (
        "notebook",
        "Your thesis, alongside",
        "Write thesis, risks and next checks per company, then export with the evidence.",
    ),
    (
        "layers",
        "Provenance on every figure",
        "Source dates, coverage and staleness flags for profile, prices, statements and metrics.",
    ),
)


@st.cache_data(show_spinner=False)
def symbol_catalog() -> list[tuple[str, str]]:
    """Versioned NSE equity catalog as (symbol, company name) pairs."""
    with _CATALOG.open(encoding="utf-8", newline="") as stream:
        return [(row["symbol"], row["name"]) for row in csv.DictReader(stream)]


def queue_company(symbol: str) -> None:
    """Queue a provider request; callbacks run before the search widgets render."""
    st.session_state.ticker_input = symbol
    st.session_state.pending_symbol = symbol


def _queue_from_finder() -> None:
    choice = st.session_state.get("company-finder")
    if choice:
        queue_company(str(choice))
    st.session_state["company-finder"] = None


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


def _active_section(has_company: bool) -> str:
    if st.session_state.show_home or not has_company:
        return "home"
    view = st.session_state.get("workspace_view") or "Overview"
    return {"Compare": "compare", "Notebook": "notebook"}.get(view, "company")


def render_sidebar() -> None:
    bundle = st.session_state.current_bundle
    has_company = isinstance(bundle, AnalysisBundle)
    active = _active_section(has_company)
    with st.sidebar:
        st.html(kit.brand_lockup("Fundamental intelligence"))
        st.html(kit.section_label("Workspace"))
        nav = (
            ("home", "Research home", "research-home", ":material/space_dashboard:", "Home"),
            (
                "company",
                "Company research",
                "company-workspace",
                ":material/analytics:",
                "Overview",
            ),
            (
                "compare",
                f"Compare companies · {len(st.session_state.compare_symbols)}/4",
                "compare-workspace",
                ":material/compare_arrows:",
                "Compare",
            ),
            (
                "notebook",
                "Research notebook",
                "notebook-workspace",
                ":material/edit_note:",
                "Notebook",
            ),
        )
        for section, label, key, icon, target in nav:
            st.button(
                label,
                key=key,
                icon=icon,
                type="secondary" if section == active else "tertiary",
                width="stretch",
                disabled=section != "home" and not has_company,
                on_click=_navigate,
                args=(target,),
            )
        st.space("small")
        st.html(kit.section_label("Recent research"))
        recent = list(st.session_state.analysis_bundles.items())[-6:]
        if not recent:
            st.caption("Companies you research appear here for one-click return.")
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
        st.space("stretch")
        st.html(
            '<div class="nv-side-card"><strong>Research support, not advice.</strong>'
            "<span>Scores organize evidence; they are not buy or sell recommendations. "
            "Notes stay in this browser session only.</span></div>"
        )
        st.html(
            f'<div class="nv-side-meta">{escape(RELEASE)} · Powered by OpenBB<br>'
            "Public access · Session-only workspace</div>"
        )


def render_hero_copy() -> None:
    st.html(
        '<div class="nv-eyebrow"><span class="nv-eyebrow-dot"></span>'
        "India equity research workspace</div>"
        '<h1 class="nv-hero-title">Know the business.<br>'
        '<span class="nv-gradient-text">Build your conviction.</span></h1>'
        '<p class="nv-hero-sub">Fundamental research for NSE and BSE companies: '
        "normalized statements, transparent scoring and source-dated evidence, "
        "in one focused workspace.</p>"
    )


def render_home(demo_mode: bool) -> None:
    catalog = symbol_catalog()
    st.space("small")
    st.html(
        '<div class="nv-stats-wrap"><div class="nv-stats nv-stats-hero">'
        + "".join(
            f'<div class="nv-stat"><div class="nv-stat-label">{escape(label)}</div>'
            f'<div class="nv-stat-value">{escape(value)}</div></div>'
            for value, label in (
                (f"{len(catalog):,}", "NSE equity listings searchable by name"),
                (str(_SCORE_PILLARS), "Score pillars, with every input inspectable"),
                ("FY + Q", "Annual and quarterly reported statements"),
                ("0", "Logins needed; your notes never leave the session"),
            )
        )
        + "</div></div>"
    )

    st.space("medium")
    with st.container(horizontal=True, vertical_alignment="bottom", gap="medium"):
        st.html(
            '<div class="nv-section-head"><div class="nv-section-kicker">Start researching</div>'
            '<div class="nv-section-title">Pick up a company</div>'
            '<p class="nv-section-sub">Quick-start companies, not investment recommendations. '
            "Select one to fetch its data.</p></div>",
            width="stretch",
        )
        if not demo_mode:
            names = dict(catalog)
            st.selectbox(
                "Find a company by name",
                list(names),
                index=None,
                format_func=lambda symbol: f"{symbol.removesuffix('.NS')} · {names[symbol]}",
                placeholder=f"Search {len(catalog):,} NSE companies…",
                key="company-finder",
                on_change=_queue_from_finder,
                width=380,
            )

    examples = [
        ("RELIANCE", "Reliance Industries", "Energy, retail & digital services"),
        ("TCS", "Tata Consultancy Services", "IT services & consulting"),
    ]
    if not demo_mode:
        examples.append(("HDFCBANK", "HDFC Bank", "Banking & financial services"))
    for column, (symbol, name, description) in zip(
        st.columns(len(examples)), examples, strict=True
    ):
        with column, st.container(key=f"card-lift-{symbol}", height="stretch"):
            with st.container(
                horizontal=True, vertical_alignment="center", gap="small", wrap=False
            ):
                st.html(kit.monogram(symbol, "md"), width="content")
                st.html(
                    f'<div><div class="nv-chip nv-chip-code">{escape(symbol)}</div>'
                    f'<div style="font-weight:650;color:var(--nv-ink);margin-top:4px">'
                    f"{escape(name)}</div></div>",
                    width="stretch",
                )
            st.caption(description)
            st.space("stretch")
            st.button(
                f"Research {symbol}",
                key=f"quick-{symbol}",
                icon=":material/arrow_forward:",
                icon_position="right",
                width="stretch",
                wrap=True,
                on_click=queue_company,
                args=(symbol,),
            )

    st.space("medium")
    st.html(
        '<div class="nv-section-head"><div class="nv-section-kicker">Why Nivesh</div>'
        '<div class="nv-section-title">One company. The full picture.</div>'
        '<p class="nv-section-sub">Understand the business, weigh sourced evidence, '
        "and develop a thesis you can defend.</p></div>"
    )
    st.html(
        '<div class="nv-features">'
        + "".join(
            f'<div class="nv-feature"><div class="nv-feature-icon">{kit.icon(name)}</div>'
            f"<h4>{escape(title)}</h4><p>{escape(body)}</p></div>"
            for name, title, body in _FEATURES
        )
        + "</div>"
    )
    st.space("small")
    with st.expander("How Nivesh handles your research", icon=":material/info:"):
        st.write(
            "Financial data comes from the configured provider through OpenBB. Source dates, "
            "coverage, and missing inputs remain visible. Scores organize research; they are "
            "not buy or sell recommendations. Recent companies and saved notes stay in this "
            "browser session only. Download your work before closing or reloading the app."
        )
