# Analyst Research Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task in the current session. User approved all work and requested no further approval gates.

**Goal:** Deliver trustworthy stock pros/cons and a portable research brief in the existing Nivesh app.

**Architecture:** Pure calculation and research services supply Streamlit and exports. Keep provider metadata attached to every dataset and observation; preserve existing missing-data and demo behavior.

**Tech Stack:** Python 3.11, Pydantic, pandas, Streamlit, Plotly, OpenBB, pytest, Playwright.

## Global constraints

- No new hosted service, account, provider or API key.
- No invented data, business claims or buy/sell recommendations.
- Five quarterly observations do not establish a 3-year CAGR.
- Missing and zero remain distinct; financial-sector industrial leverage rules remain excluded.
- Test locally before any deployment. Record provider limits separately.

### Task 1: Repair period-aware calculations

Files: services/normalization.py, new services/fundamentals.py, services/analysis.py, services/scoring.py; tests/test_fundamentals.py.

- [x] Add regressions for quarterly 3Y growth, complete/incomplete/gapped TTM, nonpositive equity, zero debt and alias normalization; run them and confirm failures against the baseline.
- [x] Implement `enrich_periods(periods, frequency='annual')`, comparable date matching and complete trailing-four-quarter helpers. Derive annual/TTM P/E and FCF yield in `fundamental_inputs(periods, metrics, frequency, market_cap=None)`; preserve provider aliases and use statement ratios consistently.
- [x] Pass frequency from both demo and live assembly, use those inputs in scoring and overview, and rerun regression tests.

Key regression:
```python
assert enrich_periods(five_quarters, 'quarterly')[-1].metrics['revenue_cagr_3y'] is None
assert fundamental_inputs(four_quarters, {'market_cap': 1000}, 'quarterly')['pe_ratio'] == 10
```

### Task 2: Build evidence-backed stock research

Files: new services/research.py, new ui/research.py, ui/overview.py; tests/test_research.py, tests/test_streamlit_app.py.

- [x] Test positive/negative observations, financial exclusions, insufficient data and export provenance before implementing.
- [x] Implement typed `ResearchObservation` and `ResearchBrief` plus `build_research_brief(bundle)` and `research_markdown(bundle, brief)`. Include actual values, comparable dates, source, valuation context and research limitations.
- [x] Render Pros, Cons, recent comparable changes and missing evidence before price history. Expose Markdown download from the same brief.
- [x] Verify both demo symbols and frequencies with AppTest and pure research tests.

Key regression:
```python
brief = build_research_brief(bundle)
assert all(item.evidence and item.source for item in (*brief.pros, *brief.cons))
assert bundle.symbol in research_markdown(bundle, brief)
```

### Task 3: Improve provenance, exports and comparisons

Files: new services/freshness.py, providers/openbb_gateway.py, services/analysis.py, ui/overview.py, ui/financials.py, services/comparison.py, ui/comparison.py; corresponding service tests.

- [x] Add source-age, unknown-date, mixed-frequency and shared-price-start regressions; verify failures.
- [x] Compute disclosed freshness from source age; preserve retrieval time separately and missing source dates. Render partial coverage honestly.
- [x] Add dated financial CSV download. Reject mixed-frequency comparisons with actionable UI text, normalize price series on the first shared positive close, and handle absent overlap.
- [x] Rerun service/UI regressions and check exported values and metadata.

Key regression:
```python
frame = normalized_price_frame(bundles)
assert frame.iloc[0].eq(100).all()
```

### Task 4: Verify and document

Files: README.md, scripts/run_checks.ps1, tests/e2e/test_app.py, dated verification document.

- [x] Extend browser coverage to research sections, annual/quarterly changes and downloads. Retain mobile, reduced-motion and WebGL coverage.
- [x] Make release checks fail on nonzero native-command exits, then run tests, lint, strict typing, component reproducibility, vulnerability audits and browser checks.
- [x] Run bounded live provider diagnostics and record source dates, actual availability, limitations and local verification results.
- [x] Self-review the full diff, update documentation and commit the tested work.

Commands use `rtk proxy .\.venv\Scripts\python.exe -m pytest -q`, `-m ruff check app.py nivesh scripts tests`, `-m mypy nivesh scripts`, `-m pytest tests/e2e -m e2e -q`, and `scripts/live_smoke.py --symbol RELIANCE.NS --timeout 45` from the repository root. Each must report its actual exit code; demo browser success does not establish live provider coverage.

Plan self-review: every approved spec section maps to one of Tasks 1–4. Service interfaces and names above are the implementation contract. Calculation and research tasks receive separate implementation and review passes.
