"""Real-browser release contracts for desktop, mobile, motion, and WebGL fallback."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from playwright.sync_api import ConsoleMessage, Page, expect


def _capture_browser_errors(page: Page) -> list[str]:
    errors: list[str] = []

    def on_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            errors.append(message.text)

    page.on("console", on_console)
    page.on("pageerror", lambda error: errors.append(str(error)))
    return errors


def _analyze(page: Page, symbol: str) -> None:
    ticker = page.get_by_label("NSE or BSE ticker")
    ticker.fill(symbol)
    page.get_by_role("button", name="Analyze").click()


def _build_comparison(page: Page, app_url: str) -> None:
    page.goto(app_url, wait_until="networkidle")
    _analyze(page, "RELIANCE")
    expect(page.get_by_text("Reliance Industries Limited")).to_be_visible()
    page.get_by_role("button", name="Add RELIANCE.NS to comparison").click()
    expect(page.get_by_role("button", name="In comparison", exact=False)).to_be_disabled()
    _analyze(page, "TCS")
    expect(page.get_by_text("Tata Consultancy Services Limited")).to_be_visible()
    page.get_by_role("button", name="Add TCS.NS to comparison").click()
    expect(page.get_by_role("button", name="In comparison", exact=False)).to_be_disabled()
    page.get_by_role("radio", name="Compare", exact=True).click()
    expect(page.get_by_text("Company comparison", exact=True)).to_be_visible()


@pytest.mark.e2e
def test_demo_analysis_and_comparison(page: Page, app_url: str) -> None:
    errors = _capture_browser_errors(page)
    _build_comparison(page, app_url)

    expect(page.get_by_text("Demo data · not a live provider result", exact=False)).to_be_visible()
    canvas = page.locator("[data-testid='financial-towers'] canvas")
    expect(canvas).to_be_visible()
    tower = page.locator("[data-testid='financial-towers']")
    canvas.focus()
    canvas.press("ArrowRight")
    expect(tower.locator("[data-detail-name]")).to_contain_text("TCS.NS")
    quality = tower.get_by_role("button", name="Quality", exact=True)
    quality.focus()
    quality.press("Enter")
    expect(page.locator("[data-detail-metric]")).to_have_text("Quality")
    for control in tower.get_by_role("button").all():
        bounds = control.bounding_box()
        assert bounds is not None and bounds["height"] >= 44
    assert errors == []


@pytest.mark.e2e
def test_mobile_analysis_has_no_page_overflow(page: Page, app_url: str) -> None:
    errors = _capture_browser_errors(page)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(app_url, wait_until="networkidle")
    _analyze(page, "RELIANCE")
    expect(page.get_by_text("Reliance Industries Limited")).to_be_visible()

    has_overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert has_overflow is False
    assert errors == []


@pytest.mark.e2e
def test_reduced_motion_preserves_metric_state(page: Page, app_url: str) -> None:
    errors = _capture_browser_errors(page)
    page.emulate_media(reduced_motion="reduce")
    _build_comparison(page, app_url)

    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches") is True
    tower = page.locator("[data-testid='financial-towers']")
    tower.get_by_role("button", name="Valuation", exact=True).click()
    expect(tower.locator("[data-detail-metric]")).to_have_text("Valuation")
    assert errors == []


@pytest.mark.e2e
def test_webgl_failure_keeps_exact_comparison_available(page: Page, app_url: str) -> None:
    errors = _capture_browser_errors(page)
    page.add_init_script(
        """
        const original = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, ...args) {
          if (String(type).startsWith('webgl')) return null;
          return original.call(this, type, ...args);
        };
        """
    )
    _build_comparison(page, app_url)

    expect(page.get_by_text("3D view unavailable", exact=False)).to_be_visible()
    expect(page.get_by_text("Fundamental comparison", exact=True)).to_be_visible()
    expect(page.locator("[data-testid='stDataFrame']")).to_be_visible()
    assert errors == []


@pytest.mark.e2e
@pytest.mark.parametrize("frequency", ["Annual", "Quarterly"])
def test_research_and_financial_downloads_keep_reporting_basis(
    page: Page,
    app_url: str,
    frequency: str,
) -> None:
    errors = _capture_browser_errors(page)
    page.goto(app_url, wait_until="networkidle")
    page.get_by_role("radio", name=frequency, exact=True).click()
    _analyze(page, "TCS")
    expect(page.get_by_text("Tata Consultancy Services Limited", exact=True)).to_be_visible()
    expect(page.get_by_text("Pros", exact=True)).to_be_visible()
    expect(page.get_by_text("Cons", exact=True)).to_be_visible()
    with page.expect_download() as downloaded:
        page.get_by_role("button", name="Download research brief (Markdown)", exact=True).click()
    report = downloaded.value
    assert f"TCS.NS-{frequency.lower()}-" in report.suggested_filename
    path = report.path()
    assert path is not None
    text = path.read_text(encoding="utf-8")
    assert "TCS.NS" in text and "DEMO" in text
    assert frequency.lower() in text
    assert "2026-03-31" in text
    assert "Pros" in text and "Cons" in text
    screenshot_dir = Path(__file__).parents[2] / "test-results" / "research"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(screenshot_dir / f"{frequency.lower()}.png"), full_page=True)
    page.get_by_role("radio", name="Financials", exact=True).click()
    expect(page.get_by_text("Financial history", exact=True)).to_be_visible()
    with page.expect_download() as downloaded_csv:
        page.get_by_role("button", name="Download financials CSV").click()
    csv_path = downloaded_csv.value.path()
    assert csv_path is not None
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows and rows[0]["Frequency"] == frequency.lower()
    assert rows[0]["Provider"] == "demo"
    assert rows[0]["Period ending"] == "2026-03-31"
    assert rows[0]["Retrieved UTC"]
    assert errors == []
