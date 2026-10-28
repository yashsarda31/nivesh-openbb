# Nivesh fundamental analyst improvements

Date: 28 October 2026
Status: approved by the user on 28 October 2026; implementation authorized without further approval gates.

## Outcome

Make each analyzed stock easier to understand, challenge and document. Its overview should explain the strongest observed fundamentals, the principal observed concerns, and what the available data cannot establish. All conclusions must remain traceable to numbers, reporting periods and providers.

## Approaches considered

1. **Recommended: reliable research brief plus calculation repairs.** Add evidence-backed pros and cons, recent financial changes, clear reporting basis and a downloadable research brief. Repair the calculations feeding those conclusions. This delivers useful daily research without additional external services.
2. **Presentation only.** Add pros and cons to the existing overview. Faster, but leaves misleading quarterly calculations underneath the text; rejected.
3. **Full research terminal.** Add filing ingestion, peer-relative valuation, forecasts and saved thesis management. Valuable later, but depends on additional datasets and a larger product design; deferred.

## Research brief

- Show Pros and Cons for every analyzed stock, immediately after its key metrics and before price history.
- Generate deterministic observations from available statements and normalized metrics: growth, margins, profitability, cash generation, cash conversion, liquidity, leverage and valuation context.
- Each observation includes the actual input value, its period or measurement basis, and its source. Trend comparisons use matching annual periods or the same quarter one year earlier.
- Never manufacture a positive or a negative to fill a column. Show an explicit no-supported-observations state when appropriate.
- Keep missing data and research questions separate from demonstrated business weaknesses. State when history is insufficient for a trend or 3-year CAGR.
- Financial companies must not receive industrial debt/equity or current-ratio conclusions. Avoid unsupported claims about management, moat, governance, pledges or competitive position.
- Valuation multiples are context, not an automatic cheap/expensive verdict without appropriate peers.
- Use explicit research wording and transparent rules. This is not a buy/sell recommendation or an AI-generated narrative based on unverified external information.

## Calculation integrity

- Pass the selected annual/quarterly basis through normalization and scoring.
- Derive 3-year CAGR only when a comparable period around three years earlier exists. Five quarterly observations do not establish a 3-year CAGR.
- Derive annual valuation yields and P/E from annual earnings/cash flow or a complete, consecutive four-quarter trailing period. Never use one quarter as annual earnings.
- Quarterly ROE/ROA must use complete trailing earnings with an appropriate balance denominator, or remain unavailable. Positive profitability must not be inferred from negative equity or negative assets.
- Preserve numeric zero, missing values, nonfinite values, negative earnings and incomplete or irregular history explicitly.
- Normalize supported provider aliases, including enterprise_to_ebitda, so overview, scoring and comparison use consistent values.
- Preserve existing coverage thresholds; missing inputs may withhold scores.

## Analyst workflow

- Show the selected frequency, latest reporting date, provider and statement-basis limitations beside the research summary.
- Display recent revenue, profit and margin changes only against comparable reporting periods.
- Add a downloadable Markdown brief containing observations, supporting data, source/retrieval dates, limitations and methodology. Add CSV download for reported financial history.
- Make source freshness distinct from fetch time. Mark source dates unavailable when unknown; do not invent them from retrieval time. Use disclosed freshness policies for prices and financial statements.
- Reject comparisons with mixed reporting frequencies. Index comparison price histories to a shared valid starting date and explain absent overlap.
- Retain the existing Streamlit structure, charts, partial-provider behavior, explicit demo labels and reduced-motion/WebGL fallbacks.

## Architecture

- Keep financial calculations in pure service helpers and use them consistently in assembly, score inputs and overview metrics.
- Implement a pure research service producing typed observations and limitations from an AnalysisBundle. The Streamlit renderer and Markdown export consume the same research result.
- Keep presentation separate from rule evaluation; no new hosted service, API key, account requirement or persistent user storage.
- Record source dates and reporting basis on derived conclusions. Do not claim consolidated/standalone status if the provider does not identify it.

## Verification

- Add adversarial regressions for quarterly CAGR, incomplete TTM earnings/cash flow, missing quarters, negative equity, zero debt, alias normalization and mixed comparison periods.
- Test research output for strong/weak fundamentals, missing data, financial-sector exclusions and evidence/date preservation.
- Verify both example stocks in annual and quarterly Streamlit workflows, report downloads and provider-limited states.
- Run the complete relevant unit/UI suite, lint and strict type checks. Run browser checks at desktop and narrow mobile sizes, including page/console errors and existing component fallbacks.
- Run a bounded real-provider smoke check separately from deterministic demo tests, preserving any provider limits in the final report.
- No deployment claim without deployment and live verification. Implementation and local testing are within this task; public release needs an explicit deployment destination.

## Current review evidence

- Repository is clean at commit 548ca77 when inspected.
- normalization.enrich_periods currently selects index minus three for 3Y CAGR regardless of frequency.
- Overview and scoring fallback P/E currently use the latest period's net income directly.
- The provider exposes enterprise_to_ebitda while the score rule currently omits that alias.
- DatasetResult.stale is not currently computed along the production assembly path.

## Spec review

Scope is limited to the existing per-company research workflow and the calculations it depends on. No placeholders, new providers, forecast promises, automated trading or external publication are included. Actual implementation and verification results will be recorded separately.
