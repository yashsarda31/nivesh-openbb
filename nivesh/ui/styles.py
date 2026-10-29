"""Existing touch-target and reduced-motion refinements over the native theme."""

from __future__ import annotations

import streamlit as st


def apply_styles() -> None:
    """Apply restrained spacing and typography refinements over native Streamlit."""

    st.html(
        """
        <style>
        :root {
          --nivesh-graphite: #1d1d1f;
          --nivesh-muted: #667085;
          --nivesh-emerald: #0a7b66;
          --nivesh-blue: #2878ff;
          --nivesh-border: rgba(29, 29, 31, 0.10);
          --nivesh-radius: 18px;
        }
        .stMainBlockContainer { max-width: 1440px; }
        [data-testid="stMetric"] {
          min-width: 10.5rem;
          box-shadow: 0 10px 32px rgba(29, 29, 31, 0.045);
        }
        [data-testid="stMetricLabel"] { color: var(--nivesh-muted); }
        [data-testid="stMetricValue"] { letter-spacing: -0.035em; }
        .stButton button,
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stSegmentedControl"] button,
        [data-testid="stTextInput"] input { min-height: 44px; }
        .stPlotlyChart { border-radius: var(--nivesh-radius); overflow: hidden; }
        @media (max-width: 640px) {
          [data-testid="stMetric"] { min-width: 9.25rem; }
        }
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after {
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
          }
        }
        </style>
        """
    )
