# Analyst research release — 28 October 2026

## Implemented

- Every analyzed company has statement-backed Pros, Cons, comparable changes, valuation context and a research checklist. Numbers, reporting dates and providers accompany observations. Missing evidence is not presented as a business weakness; zero growth stays neutral.
- Markdown research and financial CSV downloads preserve reporting frequency and provenance. INR observations use readable crore amounts; CSV retains exact reported values.
- Quarterly growth/returns and annual or complete TTM valuation calculations are corrected. Nonpositive equity/liquidity denominators cannot produce positive ratio scores. Canonical inputs and market-cap precedence are shared across overview, score and comparison.
- Provider quarterly requests use `quarter`. Missing source dates remain unknown. Income, balance and cash freshness is checked separately. Comparisons reject mixed frequencies and share a price-series baseline.
- Streamlit 1.66.1/Pillow 13.0.0 are pinned. The release runner stops on native-command failure.

## Local verification

Python 3.11, Streamlit 1.66.1:

- Full non-live/non-browser suite: **115 passed**, 7 deselected. Eight upstream OpenBB/Pydantic deprecation warnings remain.
- Chromium: **6 passed**, including desktop comparison, 390×844 mobile overflow, reduced motion, WebGL fallback and actual annual/quarterly Markdown/CSV downloads.
- Ruff: passed. Strict mypy: passed for 31 source files. `pip check`: passed.
- Requirements-resolved Python audit and installed-runtime audit: **no known vulnerabilities found**. npm audit: **0 vulnerabilities**.
- Component built twice with matching SHA-256; whitespace check passed after normalizing provider-source line endings.
- Separate review accepted the final implementation after fixing the zero-CAGR classification.

## Bounded live provider checks

- RELIANCE.NS annual: 1,234 historical prices through 27 October 2026; five statement periods through 31 March 2026; 37 provider metrics. Actual provider data generated statement-backed observations.
- TCS.NS quarterly, after fixing provider frequency mapping: 1,234 historical prices through 27 October 2026; six aligned statement dates through 30 September 2026; 37 provider metrics. Pros and Cons were generated from the actual returned statements.
- Provider metrics did not supply a source date; freshness remains unknown even after successful retrieval. Consolidated/standalone scope remains unverified. These checks establish provider availability for these requests, not universal stock coverage.

## Publication

Target: GitHub `yashsarda31/nivesh-openbb`, branch `main`, Streamlit `https://niveshopen.streamlit.app/`. Publication and deployed behavior are recorded separately after verification.

GitHub application changes were published as `777f93e`. Streamlit installed the updated main branch and Streamlit 1.66.1/Pillow 13.0.0. Its fresh resolver also selected websockets 17.3 with uvicorn 0.40.0; startup diagnostics identified an incompatible reverse-proxy handshake. Pinning the already locally tested websockets 16.1.1 fixes that deployment difference. PyArrow 24.0.0 is also pinned to the tested version; the cloud bootstrap had automatically replaced 26.0.0 due to its reported crash issue.
