# Research workspace release — 29 October 2026

## Changes
- Native navy / teal theme, dedicated research home, navigation rail, and one-click
  company research. Public access and the existing OpenBB provider remain intact.
- Recent company snapshots restore their reporting frequency without provider calls.
  At most 12 snapshots are retained, with comparison members protected from eviction.
- Overview uses a consistent metric grid, a prominent price chart, source-aware
  readiness indicators, and compact company context before the research brief.
- Price-range controls run independently of the rest of the workspace. They use
  calendar days anchored to the latest available observation, not the current date.
- Per-company/per-frequency research notebooks hold thesis, risks and next steps
  in session memory. Markdown exports include saved notes plus current source evidence.
- Refresh failures immediately show their error while retaining the last valid snapshot.

## Before deployment
- Full repository release runner passed: 120 non-browser tests, Ruff, mypy (33 files),
  requirements vulnerability audit, deterministic component builds, npm audit,
  whitespace validation, and 8 browser tests.
- Final metric-grid refinement: 11 targeted workflow tests, Ruff and mypy passed;
  all 8 browser tests passed again (31.88 seconds).
- Browser coverage includes comparison, reduced motion, WebGL fallback, 320px and
  390px layouts, annual/quarterly research and CSV exports, and notebook exports.
- Actual local TCS annual data loaded with statements through 31 March 2026 and
  historical prices through 28 October 2026. Missing source dates remained visible.

## Limits
Notes and recent companies are session-only; download before closing/reloading.
This release does not add accounts, billing, shared notes, or persistent cloud storage.
Provider coverage and source-date uncertainty remain visible. Eight upstream Python
deprecation warnings remain. Publication and live verification are recorded below
only after they are observed.
