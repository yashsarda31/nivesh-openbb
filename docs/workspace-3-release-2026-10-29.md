# Workspace 3.0 release — 29 October 2026

## Changes
- Design system: Inter / Inter Tight / JetBrains Mono typography, elevated card surfaces,
  pill tab bars, gradient primary actions, focus rings, and a dark navigation rail with a
  visible active section. Styles live in `nivesh/ui/assets/nivesh.css`; keyed containers
  (`card-*`, `home-hero`, `command-bar`, `company-header`) are the styling hooks.
- Research home: dark hero with the ticker search inside it, factual product facts
  (catalog size, score pillars, statement frequencies, no login), a company-name finder
  over the versioned NSE catalog, quick-start company cards and a feature grid.
- Company header shared by every view: monogram, name, symbol / exchange / sector chips,
  latest close with change versus the prior provider observation, and the score ring.
- Overview: KPI cards with reported-period sparklines and same-date-one-year-earlier
  deltas (shown only when the card value is that statement value; rounded zero is neutral),
  range statistics above a gradient price chart, and a per-dataset readiness list.
- Score: composite ring plus pillar bars with input counts and target weights.
- Financials: revenue, net income, free cash flow and EPS cards above the existing charts.
- Research brief: Pros / Cons cards with observation counts and accent markers.
- All provider text in custom HTML passes through `html.escape`; icons are inert
  data-URI images because `st.html` strips inline SVG.

## Unchanged
Calculations, scoring, provider semantics, demo disclosures, downloads, notebook
behaviour and public no-login access. No accounts, billing, persistence or real-time
claims were added. The score ring uses one colour so bands do not read as buy/sell signals.

## Verification
- 125 non-browser tests (120 existing + 5 new `tests/test_kit.py`), Ruff and strict mypy passed.
- Browser suite run with `--browser-channel chrome` because the installed Playwright
  Chromium build did not match Playwright 1.62.0. 9 tests passed in a full run.
- One intermittent failure reproduces on the previous commit as well: a
  `Failed to load resource: 404 /media/...` console error during the comparison flow
  (1 of 3 baseline runs). It is pre-existing and not addressed in this release.
- Live yfinance data checked locally for RELIANCE.NS (annual); demo data checked for
  every workspace view at desktop and 375px widths with no horizontal overflow.
