"""Per-company, per-frequency session notes with an explicit portable export."""

from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from nivesh.domain.models import AnalysisBundle
from nivesh.services.research import build_research_brief, research_markdown


def notebook_key(bundle: AnalysisBundle) -> str:
    period = bundle.statements.period or "annual"
    if period == "quarter":
        period = "quarterly"
    return f"{bundle.symbol}:{period}"


def notebook_markdown(bundle: AnalysisBundle, note: dict[str, str]) -> str:
    """Export saved analyst text with the exact research snapshot it describes."""
    sections = [
        f"# Research notebook · {bundle.symbol}",
        f"Reporting basis: {bundle.statements.period or 'annual'}",
        f"Saved (UTC): {note.get('saved_at', 'Not saved')}",
        "Analyst-authored notes; separate from provider evidence and automated observations.",
    ]
    for key, heading in (
        ("thesis", "Investment thesis"),
        ("risks", "Risks to the thesis"),
        ("checks", "Next research steps"),
    ):
        sections.extend([f"## {heading}", note.get(key, "").strip() or "Not recorded."])
    sections.extend(["---", research_markdown(bundle, build_research_brief(bundle))])
    return "\n\n".join(sections)


def render_notebook(bundle: AnalysisBundle) -> None:
    st.subheader("Research notebook", icon=":material/edit_note:")
    st.caption(
        "Your interpretation, alongside the evidence. Notes are separate for each company "
        "and reporting frequency."
    )
    st.info(
        "Saved in this session only. Download your notebook before closing or reloading the app.",
        icon=":material/save_alt:",
    )
    key = notebook_key(bundle)
    note = st.session_state.research_notes.get(key, {})
    with st.form(f"notebook-{key}", border=True):
        thesis = st.text_area(
            "Investment thesis",
            value=note.get("thesis", ""),
            height=150,
            placeholder="What drives the business, and what would need to be true?",
            key=f"thesis-{key}",
            max_chars=12000,
        )
        left, right = st.columns(2)
        with left:
            risks = st.text_area(
                "Risks to the thesis",
                value=note.get("risks", ""),
                height=150,
                placeholder="What evidence would change your view?",
                key=f"risks-{key}",
                max_chars=8000,
            )
        with right:
            checks = st.text_area(
                "Next research steps",
                value=note.get("checks", ""),
                height=150,
                placeholder="Filings to read, questions to resolve, metrics to monitor…",
                key=f"checks-{key}",
                max_chars=8000,
            )
        if st.form_submit_button("Save notes", type="primary", icon=":material/check:"):
            note = {
                "thesis": thesis,
                "risks": risks,
                "checks": checks,
                "saved_at": datetime.now(UTC).strftime("%d %b %Y, %H:%M UTC"),
            }
            st.session_state.research_notes = {**st.session_state.research_notes, key: note}
            st.success("Notes saved for this session.")
    if note:
        st.caption(
            f"Last saved: {note['saved_at']} · Export includes saved notes and current research."
        )
    st.download_button(
        "Download notebook (Markdown)",
        notebook_markdown(bundle, note),
        file_name=f"{bundle.symbol}-{bundle.statements.period}-notebook.md",
        mime="text/markdown",
        disabled=not bool(note),
        icon=":material/download:",
        on_click="ignore",
        key=f"notebook-export-{key}",
    )
    st.caption("Save any edits before downloading. Provider refreshes do not overwrite your notes.")
