# Nivesh

Nivesh is a public, India-first fundamental-analysis workspace for experienced analysts. It combines OpenBB-backed data retrieval, normalized annual and quarterly financials, transparent coverage-aware scores, exact Plotly charts, and a locally bundled Three.js/GSAP comparison view.

The application requires no login and stores no personal information. It is research support, not investment advice or a recommendation to buy or sell any security.

## What analysts can do

- Resolve bare NSE symbols such as `RELIANCE`, explicit `.NS` symbols, and six-digit BSE codes such as `500325.BO`.
- Inspect company identity, price history, reported financials, margins, returns, leverage, liquidity, cash generation, and supported valuation metrics.
- Switch between annual and quarterly statements.
- Review quality, growth, balance-sheet, valuation, and composite scores with every raw input, effective weight, source period, exclusion, warning, and coverage value visible.
- Compare two to four companies through indexed price charts, a sortable exact-value table, and interactive 3D financial towers.
- Continue using the charts and table when WebGL is unavailable or reduced motion is enabled.

## Local setup

Requirements: Python 3.11 and Node.js 22 or another current supported Node.js release.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm ci
npm run build:component
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501`. The default provider is OpenBB's yfinance integration and requires no credential.

### Explicit demo mode

Demo mode is disabled by default and is always labelled in the interface. It includes versioned RELIANCE and TCS fixtures for deterministic evaluation and browser tests.

```powershell
$env:NIVESH_DEMO_MODE = "true"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Never treat the demo fixtures as current market data.

## Data contracts and freshness

Each dataset carries its provider, source date, retrieval time, reporting period, currency, coverage, stale flag, and warnings. Missing values remain missing and render as `—`; they are never silently changed to numeric zero.

Production cache defaults are:

- Prices: 15 minutes.
- Profiles and provider metrics: 6 hours.
- Reported statements: 24 hours.

Refresh increments only the active provider/symbol nonce. Other analyzed companies retain their valid cache entries. Provider failures are isolated by dataset, so valid prices can remain visible when a fundamental-data route is unavailable.

Free-provider coverage for Indian companies varies by endpoint and reporting period. OpenBB is the integration foundation, not the owner of every underlying dataset. Confirm provider route support, source terms, redistribution permissions, and production licensing before public deployment. Official exchange filings remain the authority for reported results and corporate actions.

## Optional OpenBB credentials

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, or add the same `[openbb]` section in Streamlit Community Cloud. Only non-empty, allow-listed keys are applied server-side. Keys are never sent to the browser or logged.

Supported optional names are `benzinga_api_key`, `econdb_api_key`, `fmp_api_key`, `fred_api_key`, `intrinio_api_key`, `tiingo_token`, and `tradingeconomics_api_key`.

Select a provider with `NIVESH_PROVIDER`. The default remains `yfinance`.

## Scoring methodology

Metric scores use five fixed anchors with linear interpolation to 0–100. Higher-is-better and lower-is-better directions are explicit.

- Quality: ROE 35%, operating margin 35%, cash conversion 30%.
- Growth: three-year revenue CAGR 50%, three-year EPS CAGR 50%.
- Balance sheet: debt/equity 60%, current ratio 40%.
- Valuation: P/E 35%, price/book 20%, EV/EBITDA 25%, free-cash-flow yield 20%.

Missing inputs are excluded and available weights rescale only within their component. A component is withheld below 50% configured input-weight coverage. The composite gives each eligible component a 25% target weight and is withheld unless at least three components and 60% total input coverage are available. Negative P/E and EV/EBITDA values are economically unavailable, not zero-scored. Financial companies exclude the non-comparable industrial leverage component.

The methodology drawer in the app is the operational source of truth for a displayed score.

## Verification

Run the complete local release gate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_checks.ps1
```

It runs unit and Streamlit UI tests, linting, strict type checks, Python and npm vulnerability audits, deterministic component builds, whitespace checks, and Chromium tests at desktop and 390×844 mobile sizes. Browser coverage includes reduced motion, WebGL fallback, page errors, and console errors.

Run a bounded live-provider diagnostic separately:

```powershell
.\.venv\Scripts\python.exe scripts/live_smoke.py --symbol RELIANCE.NS --timeout 45
```

Exit code 0 means at least one requested live dataset returned data. Exit code 2 reports a timeout or provider-limited result; it is not an application-success claim.

The health endpoint is `/_stcore/health`.

## Streamlit Community Cloud

1. Push the repository to a private or public Git host.
2. Create a Streamlit Community Cloud app with `app.py` as the entry point.
3. Use Python 3.11.
4. Add optional `[openbb]` values in the Cloud secrets editor; do not upload a real `secrets.toml`.
5. Keep `NIVESH_DEMO_MODE` unset or false for live data.
6. Validate the health endpoint, RELIANCE analysis, partial-provider states, mobile layout, and provider terms before announcing availability.

## Docker

```powershell
docker build -t nivesh:local .
docker run --rm -p 8501:8501 nivesh:local
```

The image uses Python 3.11 slim, installs pinned runtime dependencies, runs as the non-root `nivesh` user, and exposes a container health check. Provide optional secrets through your platform's secret mechanism rather than baking them into the image.

## Troubleshooting

- No price or fundamental data: open Data health and read the provider warning, source date, and coverage before retrying. Free routes may be rate-limited or unsupported.
- A score is withheld: inspect the methodology drawer. Nivesh deliberately withholds low-coverage results.
- A ticker is rejected: use an NSE symbol containing supported letters, digits, `&`, or `-`, an explicit `.NS` suffix, or a six-digit `.BO` code.
- 3D view unavailable: the exact indexed chart and comparison table remain usable; update browser graphics support if the 3D view is desired.
- Stale output after provider recovery: use Refresh data for the active company. This does not clear other companies.
- Container is unhealthy: check `http://localhost:8501/_stcore/health` and verify the process can bind port 8501.

## Security and operating limits

Ticker input is length-limited and allow-listed. Provider values are serialized into a finite, field-allow-listed component payload; they are never interpolated as executable JavaScript. Three.js and GSAP are pinned and bundled locally, with no runtime CDN dependency. Caches are bounded, secrets stay server-side, and the public app has no authentication or personal-data surface.

Nivesh does not provide portfolio storage, alerts, trade execution, brokerage connectivity, or personalized advice.
