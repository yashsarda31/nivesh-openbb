"""Design-system layer over the native Streamlit theme.

Keyed containers carry ``st-key-<key>`` classes; ``card-*`` keys opt into the
elevated surface, and the home hero / command bar have their own hooks.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).parent / "assets" / "nivesh.css"


def apply_styles() -> None:
    """Apply the Nivesh design system over native Streamlit elements."""

    st.html(f"<style>\n{_CSS_PATH.read_text(encoding='utf-8')}</style>")
