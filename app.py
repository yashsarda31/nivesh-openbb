"""Nivesh Streamlit entry point."""

import streamlit as st

from nivesh.ui.app import run_app

st.set_page_config(
    page_title="Nivesh · India fundamental intelligence",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="auto",
)

run_app()
