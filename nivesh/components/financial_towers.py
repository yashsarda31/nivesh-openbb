"""Validated Python wrapper for the locally bundled financial towers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from math import isfinite
from pathlib import Path
from typing import Any

import streamlit as st

_ASSET_DIR = Path(__file__).parent / "assets"
_SYMBOL = re.compile(r"^[A-Z0-9&.-]{1,24}$")
_METRICS = ("composite", "quality", "growth", "balance_sheet", "valuation")


def _asset(name: str) -> str:
    content = (_ASSET_DIR / name).read_text(encoding="utf-8")
    return f"\n{content}"


_HTML = _asset("towers.html")
_CSS = _asset("towers.css")
_JS = _asset("towers.js")


def sanitize_tower_companies(
    companies: Sequence[Mapping[str, Any]],
) -> list[dict[str, object]]:
    """Allow-list identifiers and finite score values before browser serialization."""

    sanitized: list[dict[str, object]] = []
    for company in companies[:4]:
        symbol = str(company.get("symbol", "")).upper()
        name = str(company.get("name", ""))
        if not _SYMBOL.fullmatch(symbol):
            raise ValueError("Tower symbol contains unsupported characters.")
        if not 1 <= len(name) <= 80:
            raise ValueError("Tower company name must contain 1-80 characters.")
        raw_values = company.get("values")
        if not isinstance(raw_values, Mapping):
            raise ValueError("Tower values must be a metric mapping.")
        values: dict[str, float | None] = {}
        for metric in _METRICS:
            raw = raw_values.get(metric)
            if raw is None or isinstance(raw, bool):
                values[metric] = None
                continue
            if not isinstance(raw, int | float):
                values[metric] = None
                continue
            number = float(raw)
            values[metric] = max(0.0, min(100.0, number)) if isfinite(number) else None
        sanitized.append({"symbol": symbol, "name": name, "values": values})
    return sanitized


def render_financial_towers(
    companies: Sequence[Mapping[str, Any]],
    *,
    key: str = "financial-towers",
) -> None:
    """Mount an accessible Three.js comparison while exact tables remain available."""

    safe_companies = sanitize_tower_companies(companies)
    # AppTest creates isolated component managers while Python modules stay cached.
    # Public registration is idempotent, so registering at the mount boundary keeps
    # both real server reruns and isolated test runtimes correct.
    renderer = st.components.v2.component(
        "nivesh_financial_towers",
        html=_HTML,
        css=_CSS,
        js=_JS,
        isolate_styles=True,
    )
    renderer(data={"companies": safe_companies}, key=key, height=540, width="stretch")
