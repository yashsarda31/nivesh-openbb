"""Escaped HTML building blocks for the workspace chrome.

Every dynamic value passes through ``html.escape``; provider text is never trusted markup.
"""

from __future__ import annotations

from base64 import b64encode
from collections.abc import Sequence
from html import escape
from typing import Literal

Tone = Literal["ok", "warn", "bad", "muted"]

_ICONS = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
    "gauge": '<path d="M12 14 16 9"/><path d="M3.5 18a9 9 0 1 1 17 0"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/>'
    '<path d="M16 3v4M8 3v4M3 10h18"/>',
    "bars": '<path d="M5 20V11M12 20V4M19 20v-6"/>',
    "notebook": '<path d="M6 4h10a3 3 0 0 1 3 3v13H9a3 3 0 0 1-3-3Z"/>'
    '<path d="M10 9h5M10 13h3"/>',
    "shield": '<path d="M12 3 4.5 6v6c0 4.6 3.2 7.7 7.5 9 4.3-1.3 7.5-4.4 7.5-9V6Z"/>'
    '<path d="m9 12 2 2 4-4"/>',
    "trend": '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
}


def _svg_image(svg: str, size: int, css_class: str) -> str:
    # st.html sanitizes inline <svg>; data-URI images survive and stay inert.
    encoded = b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        f'<img class="{css_class}" src="data:image/svg+xml;base64,{encoded}" '
        f'width="{size}" height="{size}" alt="">'
    )


def icon(name: str, size: int = 18, color: str = "#087F70") -> str:
    """Return a decorative stroke icon from the fixed local set."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{_ICONS[name]}</svg>'
    )
    return _svg_image(svg, size, "nv-icon")


def brand_mark(size: int = 30) -> str:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        'viewBox="0 0 32 32"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#2DD4BF"/><stop offset="1" stop-color="#6366F1"/>'
        '</linearGradient></defs><rect width="32" height="32" rx="9" fill="url(#g)"/>'
        '<path d="M9 22v-4.5M14 22v-8M19 22v-5.5M24 22V10" stroke="#fff" '
        'stroke-width="2.6" stroke-linecap="round"/></svg>'
    )
    return _svg_image(svg, size, "nv-brand-mark")


def brand_lockup(tagline: str) -> str:
    return (
        '<div class="nv-brand">'
        f"{brand_mark()}"
        '<div><div class="nv-brand-name">Nivesh</div>'
        f'<div class="nv-brand-tag">{escape(tagline)}</div></div></div>'
    )


def section_label(text: str) -> str:
    return f'<div class="nv-label">{escape(text)}</div>'


def topbar(
    crumbs: Sequence[str], pills: Sequence[tuple[str, str]], *, code: str | None = None
) -> str:
    """Breadcrumb trail plus status pills; ``pills`` are (text, tone) pairs."""
    parts = [f'<span class="nv-crumb">{escape(crumb)}</span>' for crumb in crumbs]
    if code:
        parts.append(f'<span class="nv-crumb nv-crumb-code">{escape(code)}</span>')
    trail = '<span class="nv-crumb-sep">/</span>'.join(parts)
    badges = "".join(
        f'<span class="nv-pill nv-pill-{escape(tone)}"><span class="nv-pill-dot"></span>'
        f"{escape(text)}</span>"
        for text, tone in pills
    )
    return (
        f'<div class="nv-topbar"><nav class="nv-crumbs" aria-label="Breadcrumb">{trail}</nav>'
        f'<div class="nv-pills">{badges}</div></div>'
    )


def monogram(symbol: str, size: Literal["md", "lg"] = "lg") -> str:
    letters = "".join(char for char in symbol.split(".")[0] if char.isalnum())[:2] or "—"
    return f'<div class="nv-mono nv-mono-{size}" aria-hidden="true">{escape(letters)}</div>'


def chips(items: Sequence[str], *, first_is_code: bool = True) -> str:
    rendered = []
    for index, item in enumerate(items):
        kind = "nv-chip nv-chip-code" if first_is_code and index == 0 else "nv-chip"
        rendered.append(f'<span class="{kind}">{escape(item)}</span>')
    return f'<div class="nv-chips">{"".join(rendered)}</div>'


def currency_prefix(currency: str | None) -> str:
    if currency == "INR":
        return "₹"
    return f"{currency} " if currency else ""


def quote_block(
    *,
    currency: str | None,
    close: float | None,
    change: float | None,
    caption: str,
) -> str:
    """Latest close and change versus the previous provider observation."""
    value = "—" if close is None else f"{currency_prefix(currency)}{close:,.2f}"
    if change is None:
        move = '<span class="nv-move nv-move-flat">Change unavailable</span>'
    else:
        tone = "up" if change > 0 else "down" if change < 0 else "flat"
        arrow = "▲" if change > 0 else "▼" if change < 0 else "■"
        move = (
            f'<span class="nv-move nv-move-{tone}">{arrow} {abs(change):.2%}</span>'
            '<span class="nv-move-note">vs prior close</span>'
        )
    return (
        '<div class="nv-quote">'
        f'<div class="nv-quote-label">{escape(caption)}</div>'
        f'<div class="nv-quote-value">{escape(value)}</div>'
        f'<div class="nv-quote-move">{move}</div></div>'
    )


def score_ring(score: int | None, *, size: int = 92, label: str = "Nivesh score") -> str:
    """A single-colour ring: bands are not buy/sell signals, so colour stays constant."""
    filled = max(0, min(100, score)) if score is not None else 0
    center = str(score) if score is not None else "—"
    aria = f"{label}: {score} out of 100" if score is not None else f"{label}: withheld"
    return (
        f'<div class="nv-ring" role="img" aria-label="{escape(aria)}">'
        f'<div class="nv-ring-disc" style="--nv-p:{filled};width:{size}px;height:{size}px">'
        f'<div class="nv-ring-core"><span class="nv-ring-value">{escape(center)}</span>'
        '<span class="nv-ring-unit">/ 100</span></div></div>'
        f'<div class="nv-ring-label">{escape(label)}</div></div>'
    )


def status_list(rows: Sequence[tuple[str, Tone, str, str]]) -> str:
    """Rows of (dataset, tone, status, detail) with a coloured status dot."""
    items = "".join(
        '<li class="nv-status">'
        f'<span class="nv-dot nv-dot-{escape(tone)}" aria-hidden="true"></span>'
        '<div class="nv-status-body"><div class="nv-status-top">'
        f'<span class="nv-status-name">{escape(name)}</span>'
        f'<span class="nv-status-state nv-state-{escape(tone)}">{escape(state)}</span></div>'
        f'<div class="nv-status-detail">{escape(detail)}</div></div></li>'
        for name, tone, state, detail in rows
    )
    return f'<ul class="nv-status-list">{items}</ul>'


def key_values(rows: Sequence[tuple[str, str]]) -> str:
    items = "".join(
        f'<div class="nv-kv"><dt>{escape(key)}</dt><dd>{escape(value)}</dd></div>'
        for key, value in rows
    )
    return f'<dl class="nv-kvs">{items}</dl>'


def stat_strip(rows: Sequence[tuple[str, str, str]], *, compact: bool = False) -> str:
    """Rows of (label, value, tone) where tone is "", "up" or "down"."""
    items = "".join(
        f'<div class="nv-stat"><div class="nv-stat-label">{escape(label)}</div>'
        f'<div class="nv-stat-value nv-tone-{escape(tone or "flat")}">{escape(value)}</div></div>'
        for label, value, tone in rows
    )
    variant = " nv-stats-compact" if compact else ""
    return f'<div class="nv-stats-wrap"><div class="nv-stats{variant}">{items}</div></div>'


def component_bars(rows: Sequence[tuple[str, int | None, float, str]]) -> str:
    """Score components as (label, score, coverage, note) horizontal bars."""
    items = []
    for label, score, coverage, note in rows:
        width = max(0, min(100, score)) if score is not None else 0
        value = f"{score}" if score is not None else "Withheld"
        items.append(
            '<div class="nv-bar-row">'
            f'<div class="nv-bar-head"><span class="nv-bar-label">{escape(label)}</span>'
            f'<span class="nv-bar-value">{escape(value)}'
            f'{"<small>/100</small>" if score is not None else ""}</span></div>'
            f'<div class="nv-bar-track"><div class="nv-bar-fill" style="width:{width}%">'
            "</div></div>"
            f'<div class="nv-bar-note">{coverage:.0%} input coverage · {escape(note)}</div>'
            "</div>"
        )
    return f'<div class="nv-bars">{"".join(items)}</div>'


def footer(provider: str, release: str) -> str:
    return (
        '<footer class="nv-footer">'
        f'<div class="nv-footer-brand">{brand_mark(20)}<span>Nivesh</span>'
        f'<span class="nv-footer-sep">·</span><span>{escape(release)}</span></div>'
        '<div class="nv-footer-note">Research support, not investment advice or a '
        "recommendation to buy or sell any security. Verify exchange filings before acting."
        "</div>"
        f'<div class="nv-footer-meta">Data via OpenBB · {escape(provider)} · '
        "Methodology nivesh-v1 · No login, no stored notes</div>"
        "</footer>"
    )
