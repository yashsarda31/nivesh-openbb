"""Streamlit workflow tests for the public analyst workspace."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "../app.py"


def test_demo_mode_is_explicitly_labelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")

    app = AppTest.from_file(APP_PATH).run(timeout=20)

    assert not app.exception
    assert not any("Missing Submit Button" in item.value for item in app.warning)
    assert any("Demo data" in item.value for item in app.info)


def test_invalid_symbol_stays_in_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    app = AppTest.from_file(APP_PATH).run(timeout=20)

    app.text_input(key="ticker_input").set_value("../../etc")
    app.button(key="analyze_button").click().run(timeout=20)

    assert app.text_input(key="ticker_input").value == "../../etc"
    assert any("NSE symbol" in item.value for item in app.error)


def test_valid_demo_company_renders_analysis_and_methodology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    app = AppTest.from_file(APP_PATH).run(timeout=20)

    app.text_input(key="ticker_input").set_value("RELIANCE")
    app.button(key="analyze_button").click().run(timeout=20)

    assert not app.exception
    assert any("Reliance Industries Limited" in item.value for item in app.subheader)
    assert any(metric.label == "Nivesh score" for metric in app.metric)
    assert any("Research support" in item.value for item in app.caption)
    assert any("Research brief" in item.value for item in app.subheader)
    assert any(item.value == "**Pros**" for item in app.markdown)
    assert any(item.value == "**Cons**" for item in app.markdown)
    assert any("Consolidated/standalone" in item.value for item in app.markdown)


def test_refresh_preserves_active_demo_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    app.text_input(key="ticker_input").set_value("RELIANCE")
    app.button(key="analyze_button").click().run(timeout=20)

    app.button(key="refresh-current").click().run(timeout=20)

    assert not app.exception
    assert any("Reliance Industries Limited" in item.value for item in app.subheader)
    assert app.session_state["refresh_nonces"] == {"demo:RELIANCE.NS": 1}


def test_unsupported_demo_symbol_is_not_silently_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    app = AppTest.from_file(APP_PATH).run(timeout=20)

    app.text_input(key="ticker_input").set_value("INFY")
    app.button(key="analyze_button").click().run(timeout=20)

    assert any("not included in demo data" in item.value for item in app.error)
    assert not any("Reliance Industries Limited" in item.value for item in app.subheader)


def test_two_demo_companies_can_be_compared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    app = AppTest.from_file(APP_PATH).run(timeout=20)

    app.text_input(key="ticker_input").set_value("RELIANCE")
    app.button(key="analyze_button").click().run(timeout=20)
    app.button(key="add-current-to-compare").click().run(timeout=20)

    app.text_input(key="ticker_input").set_value("TCS")
    app.button(key="analyze_button").click().run(timeout=20)
    app.button(key="add-current-to-compare").click().run(timeout=20)
    app.segmented_control(key="workspace_view").set_value("Compare").run(timeout=20)

    assert not app.exception
    assert any("Company comparison" in item.value for item in app.subheader)
    assert any("RELIANCE.NS" in item.value for item in app.caption)
    assert any("TCS.NS" in item.value for item in app.caption)
