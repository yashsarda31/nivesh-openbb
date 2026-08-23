# Nivesh — India Fundamental Intelligence

## Purpose

Nivesh is a production-ready, publicly accessible Streamlit application for experienced analysts researching Indian listed companies. It uses OpenBB as the financial-data foundation and combines precise two-dimensional analysis with an optional Three.js comparison view and restrained GSAP motion.

The product must make data provenance and limitations visible. Missing values remain unavailable, stale values are labelled, and provider failures never become false zeroes or fabricated estimates.

## Scope

Version 1 supports:

- NSE and BSE ticker entry, including automatic normalization of bare NSE symbols.
- A single-company overview with profile, price, key ratios, financial history, and data-health information.
- Annual and quarterly trend analysis for income statement, balance sheet, cash flow, profitability, growth, leverage, and valuation metrics when supplied by the selected provider.
- Transparent quality, growth, balance-sheet, valuation, and composite scores.
- Visual comparison of up to four companies through precise charts, a sortable table, and an interactive Three.js scene.
- Free OpenBB-compatible providers by default and optional premium provider credentials through Streamlit secrets.
- Responsive desktop, tablet, and mobile layouts without authentication.
- Streamlit Community Cloud and Docker deployment packaging.

Version 1 does not include portfolios, saved watchlists, alerts, trade execution, personalized recommendations, buy/sell calls, user accounts, or proprietary financial forecasts.

## Product principles

1. **Analytical precision first.** The 3D scene supplements charts and tables; it never becomes the only representation of a value.
2. **Provenance is part of the interface.** Every dataset exposes its provider, reporting period, currency, retrieval time, freshness, and warnings.
3. **Unavailable is not zero.** Missing, unsupported, stale, and failed values have distinct states.
4. **Scoring is inspectable.** Users can see every input, transformation, weight, exclusion, and coverage figure.
5. **Motion explains change.** Animation is used for transitions between metrics and views, not decorative distraction.

## Information architecture

### Global header

The sticky header contains the Nivesh identity, an NSE/BSE ticker search field, Analyze action, data refresh action, provider-health indicator, and a comparison tray holding up to four companies.

Bare symbols such as `RELIANCE` normalize to `RELIANCE.NS`. Explicit symbols such as `RELIANCE.NS` and `500325.BO` remain unchanged after validation. The interface shows the resolved symbol before requesting data.

### Company overview

The overview presents company name, exchange, sector, industry, latest available price, market capitalization, reporting date, and data provenance. Headline cards cover valuation, profitability, growth, balance-sheet strength, and cash generation. Cards show an em dash and an explanatory tooltip when unavailable.

### Financial history

Analysts can switch between annual and quarterly periods and inspect:

- Revenue, EBITDA, operating profit, net income, and EPS.
- Operating, EBITDA, and net margins.
- Total assets, equity, debt, cash, working-capital measures, and leverage.
- Operating cash flow, capital expenditure, free cash flow, and cash conversion.
- ROE, ROA, ROCE, current ratio, debt/equity, interest coverage, and other supported ratios.

Plotly supplies exact tooltips, range selection, legend controls, downloads, and accessible tabular alternatives. Financial statements use a normalized period index so comparisons align equivalent fiscal periods.

### Score workspace

The score workspace displays four component scores and one composite score, all as integers from 0 to 100:

- **Quality:** profitability, margin stability, and cash conversion.
- **Growth:** revenue and EPS growth rates plus trend consistency.
- **Balance sheet:** leverage, liquidity, and debt-service capacity.
- **Valuation:** supported earnings, book, enterprise-value, and cash-flow measures.

The default composite gives each available component a 25% target weight. Missing metrics are excluded and weights are rescaled only within a component. A component is published only when at least half of its configured input weight is available. The composite is published only when at least three components and 60% of total configured input weight are available.

Metric transformations use documented fixed bands. Sector-relative percentiles may replace fixed bands only when at least five valid comparable companies share the same sector classification and reporting basis. Lower-is-better and higher-is-better metrics are explicitly marked. Financial companies use a separate rule profile; leverage measures that are not economically comparable are excluded rather than forced into the non-financial formula.

The methodology drawer lists raw inputs, normalized values, effective weights, exclusions, reporting periods, and score coverage. The score is research support, not a recommendation.

### Comparison workspace

The comparison tray accepts two to four companies. The workspace contains:

- Normalized price performance.
- Aligned revenue, earnings, margin, return, leverage, and valuation trends.
- Metric-by-metric bars or lines with exact values.
- A sortable comparison table with source and period annotations.
- A Three.js financial-tower scene.

Each company appears as a labelled glass-like tower. Tower height represents the active metric or component score; color and banding distinguish companies without implying positive or negative judgment. Users can rotate, zoom, select a tower, and hover or tap for exact values. Metric selection triggers a GSAP morph between tower states. A visible legend, reset-view control, keyboard-operable metric selector, and mirrored data table preserve interpretability.

The scene stops rendering when not visible, caps device pixel ratio, uses touch-safe controls, and loads only when the comparison workspace is opened. Reduced-motion mode shortens or removes interpolation without changing the selected data state. If WebGL or JavaScript fails, the comparison charts and table remain fully usable.

## Visual system

The interface uses a warm-white canvas, graphite typography, restrained emerald and blue data accents, generous spacing, thin borders, subtle shadows, and translucent surfaces used sparingly. System fonts provide an Apple-like typographic rhythm without downloading proprietary fonts.

The desktop layout is a structured analytical grid rather than a marketing page. Tablet layouts reduce columns while preserving side-by-side comparisons. Mobile layouts stack cards, keep primary actions reachable, simplify the 3D viewport, and allow tables to scroll horizontally with pinned identifiers.

All controls have visible focus states, semantic labels, adequate contrast, and touch targets. Color is never the sole status indicator.

## Architecture

The codebase is divided into focused modules:

```text
app.py                         Streamlit entry point and page orchestration
nivesh/config.py               Environment, provider, cache, and feature settings
nivesh/domain/                 Typed financial models and data contracts
nivesh/providers/              OpenBB adapter and provider-error translation
nivesh/services/               Normalization, ratios, scoring, and comparisons
nivesh/ui/                     Streamlit sections, formatting, and UX state
nivesh/components/             Three.js/GSAP component wrapper and assets
tests/                         Unit, contract, Streamlit, and browser checks
```

The Streamlit layer never consumes raw provider records directly. The OpenBB adapter returns a normalized result envelope:

```text
data, provider, as_of, period, currency, stale, warnings, coverage
```

Typed domain models distinguish a missing value from numeric zero. Provider-specific field names, fiscal periods, currencies, and error messages are normalized at the adapter boundary.

The Three.js component receives only sanitized comparison JSON. Three.js and GSAP are pinned and bundled locally with the component instead of relying on mutable runtime CDN assets.

## Data retrieval and freshness

The default provider configuration must work without paid credentials. Optional provider keys are read only from environment variables or Streamlit secrets and never sent to the browser or committed.

Provider calls use bounded timeouts, small retry counts with backoff, and dataset isolation. A statement-provider failure does not prevent valid price or profile data from rendering. The interface aggregates warnings in a visible data-health panel.

Caching is scoped by resolved ticker, provider, endpoint, period, and query parameters. Suggested production defaults are 15 minutes for price history, six hours for profiles and ratios, and 24 hours for reported statements. The Refresh action invalidates only the active company's cached records and requests new data. The data-health panel always shows the actual retrieval and source dates.

Provider availability, route support, redistribution terms, and production licensing must be verified against current official documentation before deployment. Unsupported data is omitted with an explanation.

## Error states

- Invalid ticker: preserve the entered value and show accepted NSE/BSE examples.
- No provider result: show the provider attempted, timestamp, and retry option.
- Partial result: render available sections and mark unavailable sections individually.
- Stale result: render with a persistent stale label and source date.
- Rate limit or timeout: preserve current valid data, show a non-blocking warning, and prevent retry storms.
- Score coverage failure: show component inputs but withhold the component or composite score.
- Three.js failure: replace the canvas with the equivalent chart and table, without blocking analysis.

Sample data is permitted only in an explicit demo mode that is disabled by default and visibly labelled throughout the interface.

## Security and operations

The public application stores no personal information and has no authentication surface. Ticker input is length-limited and allow-listed to supported symbol characters and suffixes. Comparison payloads are serialized rather than interpolated as executable JavaScript.

Secrets remain server-side. Logs avoid credentials and record provider, route, duration, status, and a request correlation identifier. Dependencies are pinned, checked for known vulnerabilities before release, and updated through deliberate compatibility testing.

The repository includes a secrets template, environment documentation, Streamlit configuration, health check, Dockerfile, deployment guide, and an operational troubleshooting section. Deployment is not part of the initial build unless separately requested.

## Testing strategy

Automated tests cover:

- NSE/BSE ticker validation and normalization.
- OpenBB adapter mapping, timeouts, partial failures, and provider warnings.
- Zero versus missing-value behavior.
- Fiscal-period alignment, ratios, score transformations, coverage thresholds, and sector rules.
- Comparison alignment and JSON sanitization.
- Streamlit rendering and state changes through `streamlit.testing.v1.AppTest`.
- Three.js component initialization, metric switching, reduced motion, fallback behavior, and console errors in a browser.

Verification includes linting, type checks, unit and integration tests with provider calls mocked by default, a bounded live-provider smoke test, dependency audit, and browser checks at desktop and 390-by-844 mobile viewports. Live tests report provider limitations rather than treating unavailable premium data as an application failure.

## Acceptance criteria

The build is acceptable when:

1. A user can enter a valid Indian ticker and obtain a clearly sourced overview without credentials when the default provider is available.
2. Missing and failed values never render as numeric zero unless the source explicitly returned zero.
3. Annual and quarterly financial trends render with aligned periods and exact tooltips.
4. Every published score exposes its formula, effective weights, source periods, and coverage.
5. Two to four companies can be compared through charts, a table, and the interactive Three.js scene.
6. GSAP transitions preserve the correct selected values and reduced-motion mode does not skip content.
7. The complete analysis remains usable when WebGL is unavailable.
8. Desktop and mobile browser checks pass without uncaught errors or blocked primary actions.
9. Automated tests, linting, type checks, and dependency checks pass before any deployment.
10. Setup and deployment documentation enables Streamlit Community Cloud or Docker operation without committing secrets.
