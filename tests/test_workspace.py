"""Behavior contracts for recent research, notebook isolation, and chart windows."""

from datetime import UTC, date, datetime

import pytest
from streamlit.testing.v1 import AppTest

from nivesh.domain.models import PricePoint
from nivesh.services.analysis import load_demo_analysis
from nivesh.ui.notebook import notebook_key, notebook_markdown
from nivesh.ui.overview import price_window


def _app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    return AppTest.from_file("../app.py").run(timeout=20)


def test_quick_start_and_recent_restore_reporting_basis(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(monkeypatch)
    app.segmented_control(key="frequency").set_value("Quarterly")
    app.button(key="quick-TCS").click().run(timeout=20)
    assert not app.exception
    assert app.session_state.current_bundle.symbol == "TCS.NS"
    assert app.session_state.current_bundle.statements.period == "quarterly"
    app.button(key="research-home").click().run(timeout=20)
    app.segmented_control(key="frequency").set_value("Annual")
    app.button(key="quick-RELIANCE").click().run(timeout=20)
    app.button(key="recent-TCS.NS").click().run(timeout=20)
    assert not app.exception
    assert app.text_input(key="ticker_input").value == "TCS.NS"
    assert app.segmented_control(key="frequency").value == "Quarterly"
    assert app.session_state.current_bundle.symbol == "TCS.NS"


def test_notes_survive_navigation_refresh_and_company_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(monkeypatch)
    app.button(key="quick-TCS").click().run(timeout=20)
    app.button(key="notebook-workspace").click().run(timeout=20)
    app.text_area(key="thesis-TCS.NS:annual").set_value("Monitor cash conversion.")
    app.text_area(key="risks-TCS.NS:annual").set_value("Customer concentration.")
    next(button for button in app.button if button.label == "Save notes").click().run(timeout=20)
    assert not app.exception
    assert app.session_state.research_notes["TCS.NS:annual"]["thesis"] == "Monitor cash conversion."
    app.button(key="refresh-current").click().run(timeout=20)
    app.button(key="research-home").click().run(timeout=20)
    app.button(key="quick-RELIANCE").click().run(timeout=20)
    app.button(key="notebook-workspace").click().run(timeout=20)
    assert app.text_area(key="thesis-RELIANCE.NS:annual").value == ""
    app.button(key="recent-TCS.NS").click().run(timeout=20)
    app.button(key="notebook-workspace").click().run(timeout=20)
    assert app.text_area(key="thesis-TCS.NS:annual").value == "Monitor cash conversion."
    assert not app.exception


def test_notebook_export_preserves_notes_and_snapshot_provenance() -> None:
    annual = load_demo_analysis("TCS.NS", "annual")
    quarterly = load_demo_analysis("TCS.NS", "quarterly")
    assert notebook_key(annual) != notebook_key(quarterly)
    text = notebook_markdown(quarterly, {"thesis": "My thesis", "risks": "My risk"})
    assert "My thesis" in text and "My risk" in text
    assert "quarterly" in text and "TCS.NS" in text and "DEMO" in text
    assert "Retrieved" in text or "retrieved" in text


def test_price_window_anchors_to_source_date_and_preserves_exact_points() -> None:
    points = [
        PricePoint(date=datetime(2024, 3, 31, tzinfo=UTC), close=120),
        PricePoint(date=date(2024, 1, 1), close=100),
        PricePoint(date=date(2024, 3, 1), close=110),
    ]
    assert [point.close for point in price_window(points, "1M")] == [110, 120]
    assert [point.close for point in price_window(points, "All")] == [100, 110, 120]
    assert price_window([], "1M") == []


def test_refresh_error_is_immediately_visible_and_keeps_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app(monkeypatch)
    app.button(key="quick-TCS").click().run(timeout=20)
    previous = app.session_state.current_bundle

    def fail(*args, **kwargs):
        raise RuntimeError("Provider unavailable")

    monkeypatch.setattr("nivesh.ui.app._load_bundle", fail)
    app.button(key="refresh-current").click().run(timeout=20)
    assert app.session_state.current_bundle == previous
    assert any("Refresh failed" in error.value for error in app.error)
    assert not app.exception
