# Nivesh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready, public Streamlit application for analyst-grade fundamental analysis and visual comparison of Indian equities using OpenBB, Plotly, Three.js, and GSAP.

**Architecture:** A thin Streamlit shell consumes typed, provider-neutral domain objects from an OpenBB gateway. Pure services normalize statements, calculate ratios and transparent scores, and align comparisons; Plotly renders exact analytical charts while a locally bundled Streamlit Components v2 module renders the supplemental Three.js view with GSAP transitions.

**Tech Stack:** Python 3.11, Streamlit 1.61.1, OpenBB 4.7.2 with the yfinance provider, Plotly 6.9.0, Pydantic 2.x as resolved by OpenBB, pytest 9.1.1, Three.js 0.185.1, GSAP 3.15.0, esbuild 0.28.2, Playwright 1.62.0.

## Global Constraints

- India-first: accept bare NSE symbols, explicit `.NS` symbols, and six-digit `.BO` symbols.
- Public access without login; store no personal information.
- Free-provider baseline; optional premium credentials are server-side secrets only.
- Missing values remain `None` and render as `—`; never coerce missing data to zero.
- Every dataset exposes provider, source date, retrieval time, period, currency, freshness, warnings, and coverage.
- Publish a component score only at 50% input-weight coverage; publish the composite only with three components and 60% total coverage.
- Comparison supports two to four companies.
- Plotly charts and tables remain the exact-value source of truth; the Three.js scene is supplemental.
- Respect reduced motion and provide a fully usable non-WebGL path.
- Pin runtime and frontend dependencies and test before any deployment.
- Demo data is disabled by default and visibly labelled whenever enabled.
- Public modules and functions use concise docstrings; non-obvious financial formulas, provider mappings, and WebGL cleanup logic include maintainability comments.

---

## Planned file structure

```text
.streamlit/config.toml                  Streamlit theme and server settings
.streamlit/secrets.toml.example         Documented secret names without values
app.py                                  Minimal Streamlit entry point
pyproject.toml                          Project metadata and tool configuration
requirements.txt                        Exact production dependencies
requirements-dev.txt                    Exact development/test dependencies
package.json                            Exact Three.js, GSAP, and esbuild versions
package-lock.json                       Reproducible frontend dependency graph
Dockerfile                              Production container
.dockerignore                           Container exclusions
.gitignore                              Local, secret, cache, and build exclusions
README.md                               Setup, use, methodology, and deployment guide
nivesh/config.py                        Validated settings and provider selection
nivesh/domain/models.py                 Typed provider-neutral financial contracts
nivesh/providers/openbb_gateway.py      OpenBB calls and provider error translation
nivesh/services/tickers.py              Indian ticker validation and normalization
nivesh/services/normalization.py        Statement normalization and period alignment
nivesh/services/ratios.py               Safe derived metric calculations
nivesh/services/scoring.py              Transparent fixed-band scoring
nivesh/services/comparison.py           Cross-company alignment and table payloads
nivesh/services/loaders.py              Streamlit caching and targeted refresh
nivesh/ui/app.py                        Session state and page orchestration
nivesh/ui/styles.py                     Apple-inspired CSS tokens and responsive rules
nivesh/ui/overview.py                   Company overview and data health
nivesh/ui/financials.py                 Historical statements and Plotly charts
nivesh/ui/scores.py                     Score cards and methodology drawer
nivesh/ui/comparison.py                 Compare tray, charts, table, and 3D mount
nivesh/ui/charts.py                     Pure Plotly figure factories
nivesh/components/financial_towers.py   Components v2 Python registration/wrapper
nivesh/components/assets/towers.html    Semantic component markup
nivesh/components/assets/towers.css     Component-only responsive styles
nivesh/components/assets/towers.js      Generated, locally bundled browser module
component_frontend/src/towers.js        Readable Three.js/GSAP source
component_frontend/build.mjs            Deterministic esbuild entry point
nivesh/assets/india_symbols.csv         Versioned NSE/BSE lookup snapshot
nivesh/assets/demo/RELIANCE.NS.json     Explicit Reliance demo analysis fixture
nivesh/assets/demo/TCS.NS.json          Explicit TCS demo analysis fixture
scripts/update_symbols.py               Validated NSE symbol-master updater
scripts/live_smoke.py                    Bounded live OpenBB smoke check
scripts/run_checks.ps1                   Reproducible local release gate
tests/fixtures/                          Small provider and statement fixtures
tests/e2e/test_app.py                    Browser workflow and responsive checks
tests/test_*.py                          Unit, contract, and Streamlit tests
```

---

### Task 1: Reproducible project foundation and typed contracts

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.streamlit/config.toml`
- Create: `nivesh/__init__.py`
- Create: `nivesh/config.py`
- Create: `nivesh/domain/__init__.py`
- Create: `nivesh/domain/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `AppSettings.from_mapping(mapping) -> AppSettings`
- Produces: `DatasetResult[T]`, `CompanyProfile`, `PricePoint`, `FinancialPeriod`, `AnalysisBundle`, `MetricScore`, `ComponentScore`, and `Scorecard`.

- [ ] **Step 1: Add pinned dependency and tool configuration**

Create `requirements.txt`:

```text
openbb==4.7.2
plotly==6.9.0
streamlit==1.61.1
```

Create `requirements-dev.txt`:

```text
-r requirements.txt
mypy==2.3.0
pip-audit==2.10.1
playwright==1.62.0
pytest==9.1.1
pytest-playwright==0.9.0
ruff==0.15.22
```

Set `requires-python = ">=3.11,<3.12"` in `pyproject.toml`; configure pytest markers `live` and `e2e`, Ruff line length 100, and mypy with `strict = true` plus `ignore_missing_imports = true`.

- [ ] **Step 2: Create the environment and verify dependency resolution**

Run:

```powershell
rtk py -3.11 -m venv .venv
rtk .\.venv\Scripts\python.exe -m pip install --upgrade pip
rtk .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Expected: all packages install without a resolver conflict; OpenBB resolves a Ruff version below 0.16.

- [ ] **Step 3: Write failing missing-versus-zero and settings tests**

```python
from datetime import UTC, datetime

from nivesh.config import AppSettings
from nivesh.domain.models import DatasetResult


def test_dataset_result_preserves_zero_and_none() -> None:
    result = DatasetResult[dict[str, float | None]](
        data={"market_cap": 0.0, "free_cash_flow": None},
        provider="fixture",
        retrieved_at=datetime.now(UTC),
        coverage=0.5,
    )
    assert result.data["market_cap"] == 0.0
    assert result.data["free_cash_flow"] is None


def test_settings_default_to_free_provider() -> None:
    settings = AppSettings.from_mapping({})
    assert settings.provider == "yfinance"
    assert settings.demo_mode is False
    assert settings.price_ttl_seconds == 900
```

- [ ] **Step 4: Run the tests and confirm the import failure**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_models.py -v`

Expected: FAIL because `nivesh.config` and `nivesh.domain.models` do not exist.

- [ ] **Step 5: Implement the contracts and validated settings**

Use Pydantic models with explicit optional values:

```python
class DatasetResult(BaseModel, Generic[T]):
    data: T
    provider: str
    retrieved_at: datetime
    as_of: date | datetime | None = None
    period: str | None = None
    currency: str | None = None
    stale: bool = False
    warnings: tuple[str, ...] = ()
    coverage: float = Field(default=1.0, ge=0.0, le=1.0)


class FinancialPeriod(BaseModel):
    period_ending: date
    fiscal_period: str | None = None
    fiscal_year: int | None = None
    currency: str | None = None
    revenue: float | None = None
    operating_income: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    diluted_eps: float | None = None
    total_assets: float | None = None
    total_equity: float | None = None
    total_debt: float | None = None
    cash: float | None = None
    total_current_assets: float | None = None
    total_current_liabilities: float | None = None
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    free_cash_flow: float | None = None
    metrics: dict[str, float | None] = Field(default_factory=dict)
```

Define `AppSettings.from_mapping` to read `NIVESH_PROVIDER`, `NIVESH_DEMO_MODE`, `NIVESH_PRICE_TTL`, `NIVESH_PROFILE_TTL`, and `NIVESH_STATEMENT_TTL`, with defaults `yfinance`, `false`, `900`, `21600`, and `86400`.

- [ ] **Step 6: Run quality checks and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_models.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh tests
rtk .\.venv\Scripts\mypy.exe nivesh
rtk git add .gitignore pyproject.toml requirements.txt requirements-dev.txt .streamlit nivesh tests/test_models.py
rtk git commit -m "build: establish Nivesh domain foundation"
```

Expected: tests, lint, and types PASS; one focused commit is created.

---

### Task 2: Indian ticker validation and searchable symbol catalog

**Files:**
- Create: `nivesh/services/__init__.py`
- Create: `nivesh/services/tickers.py`
- Create: `scripts/update_symbols.py`
- Create: `tests/fixtures/EQUITY_L_sample.csv`
- Create: `nivesh/assets/india_symbols.csv`
- Test: `tests/test_tickers.py`

**Interfaces:**
- Produces: `resolve_symbol(raw: str) -> ResolvedTicker`
- Produces: `search_symbols(query: str, rows: Sequence[SymbolRecord], limit: int = 8) -> list[SymbolRecord]`
- Produces: `parse_nse_symbol_master(csv_text: str, as_of: date) -> list[SymbolRecord]`

- [ ] **Step 1: Write failing normalization and catalog tests**

```python
import pytest

from nivesh.services.tickers import SymbolValidationError, resolve_symbol


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("reliance", "RELIANCE.NS"), ("M&M.NS", "M&M.NS"), ("500325.bo", "500325.BO")],
)
def test_resolve_symbol(raw: str, expected: str) -> None:
    assert resolve_symbol(raw).symbol == expected


@pytest.mark.parametrize("raw", ["", "../../etc", "RELIANCE<script>", "A" * 31])
def test_rejects_unsafe_symbols(raw: str) -> None:
    with pytest.raises(SymbolValidationError):
        resolve_symbol(raw)
```

Add a parser test asserting the sample NSE CSV produces `RELIANCE.NS`, preserves the company name, and records the supplied snapshot date.

- [ ] **Step 2: Verify the tests fail**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_tickers.py -v`

Expected: FAIL because the ticker service is absent.

- [ ] **Step 3: Implement strict normalization and deterministic search**

```python
_BARE = re.compile(r"^[A-Z0-9&-]{1,20}$")
_NSE = re.compile(r"^[A-Z0-9&-]{1,20}\.NS$")
_BSE = re.compile(r"^[0-9]{6}\.BO$")


def resolve_symbol(raw: str) -> ResolvedTicker:
    value = raw.strip().upper()
    if _NSE.fullmatch(value):
        return ResolvedTicker(symbol=value, exchange="NSE", original=raw)
    if _BSE.fullmatch(value):
        return ResolvedTicker(symbol=value, exchange="BSE", original=raw)
    if _BARE.fullmatch(value):
        return ResolvedTicker(symbol=f"{value}.NS", exchange="NSE", original=raw)
    raise SymbolValidationError("Use an NSE symbol such as RELIANCE or a six-digit BSE code.")
```

Search is case-insensitive, ranks exact symbol matches before prefix and company-name matches, and never returns more than eight rows.

- [ ] **Step 4: Implement the validated updater**

`scripts/update_symbols.py` downloads the official NSE equity CSV URL, requires the columns `SYMBOL`, `NAME OF COMPANY`, and `SERIES`, retains `SERIES == "EQ"`, rejects an empty or malformed response, and writes sorted rows with `symbol`, `name`, `exchange`, and `snapshot_date`. The committed snapshot is generated once during implementation; production never requires this download to start.

- [ ] **Step 5: Run and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_tickers.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh scripts tests
rtk git add nivesh/services nivesh/assets scripts/update_symbols.py tests/test_tickers.py tests/fixtures/EQUITY_L_sample.csv
rtk git commit -m "feat: add Indian ticker resolution"
```

Expected: PASS and a versioned, non-empty symbol snapshot.

---

### Task 3: OpenBB gateway with isolated dataset failures

**Files:**
- Create: `nivesh/providers/__init__.py`
- Create: `nivesh/providers/openbb_gateway.py`
- Create: `tests/fixtures/openbb_payloads.py`
- Test: `tests/test_openbb_gateway.py`
- Test: `tests/test_live_openbb.py`

**Interfaces:**
- Consumes: `DatasetResult`, `CompanyProfile`, `PricePoint`, and `AppSettings`.
- Produces: `OpenBBGateway.fetch_profile(symbol)`, `fetch_prices(symbol, start_date)`, `fetch_statements(symbol, period)`, `fetch_metrics(symbol, period)`, and `fetch_analysis(symbol, period)`.

- [ ] **Step 1: Write failing gateway contract tests with a fake OpenBB client**

```python
def test_profile_maps_provider_and_preserves_missing(fake_obb: FakeOBB) -> None:
    gateway = OpenBBGateway(client=fake_obb, provider="yfinance")
    result = gateway.fetch_profile("RELIANCE.NS")
    assert result.provider == "yfinance"
    assert result.data.market_cap is None
    assert result.data.name == "Reliance Industries Limited"


def test_statement_failure_does_not_discard_prices(fake_obb: FakeOBB) -> None:
    fake_obb.raise_on.add("income")
    bundle = OpenBBGateway(fake_obb, "yfinance").fetch_analysis("RELIANCE.NS", "annual")
    assert bundle.prices.data
    assert bundle.statements.data == []
    assert "income" in " ".join(bundle.statements.warnings).lower()
```

The fake response implements `.results`, `.provider`, `.warnings`, and result `.model_dump()` so tests exercise the real adapter boundary without a provider call.

- [ ] **Step 2: Verify the tests fail**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_openbb_gateway.py -v`

Expected: FAIL because `OpenBBGateway` is undefined.

- [ ] **Step 3: Implement the gateway route map and error translation**

Use current official OpenBB routes:

```python
ROUTES = {
    "profile": lambda obb, kw: obb.equity.profile(**kw),
    "prices": lambda obb, kw: obb.equity.price.historical(**kw),
    "income": lambda obb, kw: obb.equity.fundamental.income(**kw),
    "balance": lambda obb, kw: obb.equity.fundamental.balance(**kw),
    "cash": lambda obb, kw: obb.equity.fundamental.cash(**kw),
    "metrics": lambda obb, kw: obb.equity.fundamental.metrics(**kw),
}


def _records(output: object) -> list[dict[str, object]]:
    results = getattr(output, "results", None) or []
    return [item.model_dump(exclude_none=False) for item in results]
```

Each public fetch method catches provider exceptions for its own dataset, logs route/provider/duration/correlation ID without secrets, and returns an empty `DatasetResult` with a concise warning. `fetch_analysis` assembles results without throwing away successful datasets.

- [ ] **Step 4: Add a bounded opt-in live smoke test**

```python
@pytest.mark.live
def test_live_reliance_price() -> None:
    if os.getenv("RUN_LIVE_OPENBB") != "1":
        pytest.skip("Set RUN_LIVE_OPENBB=1 for the bounded provider smoke test")
    result = OpenBBGateway.from_openbb(provider="yfinance").fetch_prices(
        "RELIANCE.NS", date.today() - timedelta(days=10)
    )
    assert result.provider == "yfinance"
    assert result.data or result.warnings
```

- [ ] **Step 5: Run contract checks and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_openbb_gateway.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh tests
rtk .\.venv\Scripts\mypy.exe nivesh
rtk git add nivesh/providers tests/test_openbb_gateway.py tests/test_live_openbb.py tests/fixtures/openbb_payloads.py
rtk git commit -m "feat: add resilient OpenBB gateway"
```

Expected: mocked tests PASS; live test SKIPS unless explicitly enabled.

---

### Task 4: Financial normalization, period alignment, and ratios

**Files:**
- Create: `nivesh/services/normalization.py`
- Create: `nivesh/services/ratios.py`
- Create: `tests/fixtures/statements.json`
- Test: `tests/test_normalization.py`
- Test: `tests/test_ratios.py`

**Interfaces:**
- Consumes: raw OpenBB statement records.
- Produces: `normalize_statements(income, balance, cash) -> list[FinancialPeriod]`
- Produces: `enrich_periods(periods) -> list[FinancialPeriod]`
- Produces: `safe_divide`, `cagr`, and `average_balance`.

- [ ] **Step 1: Write failing alignment and null-safety tests**

```python
def test_aligns_statements_by_period_ending(statement_payloads: dict[str, list[dict]]) -> None:
    periods = normalize_statements(**statement_payloads)
    assert [row.period_ending.isoformat() for row in periods] == ["2024-03-31", "2025-03-31"]
    assert periods[-1].revenue == 1_000.0
    assert periods[-1].total_debt == 0.0


def test_safe_divide_distinguishes_missing_and_zero() -> None:
    assert safe_divide(None, 10.0) is None
    assert safe_divide(0.0, 10.0) == 0.0
    assert safe_divide(10.0, 0.0) is None
```

- [ ] **Step 2: Run tests and verify failure**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_normalization.py tests/test_ratios.py -v`

Expected: FAIL because the services do not exist.

- [ ] **Step 3: Implement explicit field maps and date-keyed joins**

```python
INCOME_FIELDS = {
    "revenue": "revenue",
    "operating_income": "operating_income",
    "ebitda": "ebitda",
    "net_income": "net_income",
    "diluted_earnings_per_share": "diluted_eps",
}
BALANCE_FIELDS = {
    "total_assets": "total_assets",
    "total_equity": "total_equity",
    "total_debt": "total_debt",
    "cash_and_cash_equivalents": "cash",
    "total_current_assets": "total_current_assets",
    "total_current_liabilities": "total_current_liabilities",
}
CASH_FIELDS = {
    "operating_cash_flow": "operating_cash_flow",
    "capital_expenditure": "capital_expenditure",
    "free_cash_flow": "free_cash_flow",
}
```

Parse only finite numeric values, join records on `period_ending`, sort ascending, and retain each row's fiscal period, year, and reported currency.

- [ ] **Step 4: Implement ratios and growth without fabricated denominators**

Add operating margin, net margin, ROE using average equity, ROA using average assets, debt/equity, current ratio, operating-cash-flow conversion, free cash flow, three-year revenue CAGR, and three-year EPS CAGR. If a required input is missing, zero, non-finite, or economically invalid for the calculation, return `None` and record no substitute.

- [ ] **Step 5: Run and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_normalization.py tests/test_ratios.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh tests
rtk git add nivesh/services/normalization.py nivesh/services/ratios.py tests
rtk git commit -m "feat: normalize Indian company financials"
```

Expected: statement joins and all null/zero edge cases PASS.

---

### Task 5: Transparent analyst score and coverage rules

**Files:**
- Create: `nivesh/services/scoring.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: latest enriched `FinancialPeriod`, profile sector, and provider metrics.
- Produces: `score_company(periods, profile, metrics) -> Scorecard`
- Produces: `score_metric(value, band) -> float | None`

- [ ] **Step 1: Write failing scoring and coverage tests**

```python
def test_missing_metric_is_excluded_not_scored_zero() -> None:
    score = score_component(
        "quality",
        {"roe": 0.20, "operating_margin": None, "cash_conversion": 1.0},
    )
    assert score.score is not None
    assert score.coverage < 1.0
    assert score.metrics["operating_margin"].score is None


def test_composite_is_withheld_below_threshold() -> None:
    card = score_company(periods=minimal_periods(), profile=profile(), metrics={})
    assert card.composite is None
    assert card.coverage < 0.60


def test_financial_sector_excludes_non_comparable_leverage() -> None:
    card = score_company(periods=bank_periods(), profile=bank_profile(), metrics={})
    assert card.components["balance_sheet"].score is None
    assert "debt_equity" in card.components["balance_sheet"].excluded
```

- [ ] **Step 2: Verify failure**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_scoring.py -v`

Expected: FAIL because the scoring engine is absent.

- [ ] **Step 3: Implement fixed, documented scoring bands**

Define monotonic piecewise-linear bands:

```python
QUALITY = {
    "roe": Band((-0.05, 0.05, 0.12, 0.20, 0.30), (0, 25, 50, 75, 100)),
    "operating_margin": Band((-0.05, 0.05, 0.12, 0.20, 0.30), (0, 25, 50, 75, 100)),
    "cash_conversion": Band((0.0, 0.5, 0.8, 1.0, 1.3), (0, 25, 50, 75, 100)),
}
GROWTH = {
    "revenue_cagr_3y": Band((-0.05, 0.0, 0.08, 0.15, 0.25), (0, 25, 50, 75, 100)),
    "eps_cagr_3y": Band((-0.10, 0.0, 0.10, 0.20, 0.35), (0, 25, 50, 75, 100)),
}
BALANCE = {
    "debt_equity": Band((3.0, 2.0, 1.0, 0.5, 0.0), (0, 25, 50, 75, 100)),
    "current_ratio": Band((0.5, 0.8, 1.2, 1.8, 2.5), (0, 25, 50, 75, 100)),
}
VALUATION = {
    "pe_ratio": Band((50.0, 35.0, 25.0, 18.0, 10.0), (0, 25, 50, 75, 100)),
    "price_to_book": Band((10.0, 6.0, 4.0, 2.0, 1.0), (0, 25, 50, 75, 100)),
    "ev_to_ebitda": Band((30.0, 22.0, 15.0, 10.0, 6.0), (0, 25, 50, 75, 100)),
    "free_cash_flow_yield": Band((0.0, 0.01, 0.03, 0.05, 0.08), (0, 25, 50, 75, 100)),
}
```

Reject negative P/E and EV/EBITDA as unavailable. Publish each component only at 50% configured-weight coverage. Give components equal 25% target weights and publish the integer composite only with at least three available components and 60% total input coverage.

- [ ] **Step 4: Expose the methodology payload**

Populate `MetricScore` with raw value, score, effective weight, direction, source period, and exclusion reason. Populate `ComponentScore` and `Scorecard` with coverage and warning tuples so the UI does not reconstruct methodology.

- [ ] **Step 5: Run and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_scoring.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh tests
rtk .\.venv\Scripts\mypy.exe nivesh
rtk git add nivesh/services/scoring.py nivesh/domain/models.py tests/test_scoring.py
rtk git commit -m "feat: add transparent fundamental scoring"
```

Expected: coverage, sector exclusion, and fixed-band boundary tests PASS.

---

### Task 6: Exact-value Plotly chart factories

**Files:**
- Create: `nivesh/ui/__init__.py`
- Create: `nivesh/ui/charts.py`
- Test: `tests/test_charts.py`

**Interfaces:**
- Consumes: normalized financial periods and comparison frames.
- Produces: `financial_trend_figure`, `margin_figure`, `price_figure`, `comparison_figure`, and `empty_figure`.

- [ ] **Step 1: Write failing figure-contract tests**

```python
def test_financial_chart_keeps_exact_values(sample_periods: list[FinancialPeriod]) -> None:
    figure = financial_trend_figure(sample_periods, ["revenue", "net_income"])
    assert list(figure.data[0].y) == [800.0, 1_000.0]
    assert figure.layout.hovermode == "x unified"


def test_empty_chart_explains_unavailable_data() -> None:
    figure = financial_trend_figure([], ["revenue"])
    assert "unavailable" in figure.layout.annotations[0].text.lower()
```

- [ ] **Step 2: Verify failure**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_charts.py -v`

Expected: FAIL because chart factories do not exist.

- [ ] **Step 3: Implement shared Apple-style Plotly tokens**

Use transparent backgrounds, graphite labels, `#0A7B66` and `#2878FF` accents, unified exact-value hover templates, accessible line markers, and no Plotly logo. Figures must accept source values unchanged; formatting is limited to display text and axis ticks.

- [ ] **Step 4: Run and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_charts.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh tests
rtk git add nivesh/ui tests/test_charts.py
rtk git commit -m "feat: add financial chart system"
```

Expected: all figure contracts PASS.

---

### Task 7: Streamlit shell, search flow, overview, financials, and score UI

**Files:**
- Create: `app.py`
- Create: `nivesh/ui/app.py`
- Create: `nivesh/ui/styles.py`
- Create: `nivesh/ui/overview.py`
- Create: `nivesh/ui/financials.py`
- Create: `nivesh/ui/scores.py`
- Create: `nivesh/assets/demo/RELIANCE.NS.json`
- Create: `nivesh/assets/demo/TCS.NS.json`
- Test: `tests/test_streamlit_app.py`

**Interfaces:**
- Consumes: ticker resolver, analysis loader, charts, and scorecard.
- Produces: a complete one-company workflow and reusable `render_data_health`.

- [ ] **Step 1: Write failing AppTest flows**

```python
def test_demo_mode_is_explicitly_labelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    app = AppTest.from_file("app.py").run(timeout=20)
    assert not app.exception
    assert any("Demo data" in item.value for item in app.info)


def test_invalid_symbol_stays_in_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIVESH_DEMO_MODE", "true")
    app = AppTest.from_file("app.py").run(timeout=20)
    app.text_input(key="ticker_input").set_value("../../etc")
    app.button(key="analyze_button").click().run(timeout=20)
    assert app.text_input(key="ticker_input").value == "../../etc"
    assert any("NSE symbol" in item.value for item in app.error)
```

- [ ] **Step 2: Verify failure**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_streamlit_app.py -v`

Expected: FAIL because `app.py` does not exist.

- [ ] **Step 3: Build a thin entry point and explicit session state**

```python
import streamlit as st

from nivesh.ui.app import run_app

st.set_page_config(page_title="Nivesh", page_icon="◉", layout="wide")
run_app()
```

Initialize `active_symbol`, `compare_symbols`, `frequency`, and `refresh_nonce` once. The search form resolves the symbol before loading; it never starts a provider request for invalid input.

- [ ] **Step 4: Implement responsive visual tokens and content sections**

Use CSS custom properties for warm white, graphite, emerald, blue, borders, radius, and shadows. Render the company identity, source/date labels, key ratio cards, price and statement charts, annual/quarterly selector, score components, coverage, methodology expander, and data-health warnings. All unavailable values use `—` plus a reason.

- [ ] **Step 5: Add explicit demo fixture behavior**

Load the versioned fixture only when `NIVESH_DEMO_MODE=true`. Show a persistent `Demo data · not a live provider result` notice above all analysis. When demo mode is false, an unavailable provider produces an error state rather than the fixture.

- [ ] **Step 6: Run and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_streamlit_app.py tests/test_charts.py -v
rtk .\.venv\Scripts\ruff.exe check app.py nivesh tests
rtk .\.venv\Scripts\mypy.exe nivesh
rtk git add app.py nivesh/ui nivesh/assets/demo tests/test_streamlit_app.py
rtk git commit -m "feat: build analyst company workspace"
```

Expected: valid demo analysis renders, invalid input is preserved, and no AppTest exception occurs.

---

### Task 8: Multi-company comparison service and Streamlit workspace

**Files:**
- Create: `nivesh/services/comparison.py`
- Create: `nivesh/ui/comparison.py`
- Test: `tests/test_comparison.py`
- Modify: `nivesh/ui/app.py`

**Interfaces:**
- Consumes: two to four `AnalysisBundle` objects.
- Produces: `build_comparison(bundles) -> ComparisonPayload`
- Produces: `normalized_price_frame(bundles) -> pandas.DataFrame`
- Produces: JSON-safe tower payloads for Task 9.

- [ ] **Step 1: Write failing alignment and limit tests**

```python
def test_prices_normalize_each_company_to_100(bundles: list[AnalysisBundle]) -> None:
    frame = normalized_price_frame(bundles[:2])
    first_valid = frame.apply(lambda column: column.dropna().iloc[0])
    assert first_valid.to_dict() == {"RELIANCE.NS": 100.0, "TCS.NS": 100.0}


def test_comparison_rejects_more_than_four(bundles: list[AnalysisBundle]) -> None:
    with pytest.raises(ValueError, match="two to four"):
        build_comparison(bundles * 3)
```

- [ ] **Step 2: Verify failure**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_comparison.py -v`

Expected: FAIL because comparison services do not exist.

- [ ] **Step 3: Implement comparison alignment**

Align price history by trading date with outer joins, normalize from each series' first valid positive close, and preserve gaps. Align financials by fiscal year and period without forward filling. Produce rows containing symbol, company, metric, exact value, display value, period, currency, provider, and warning.

- [ ] **Step 4: Implement the comparison tray and exact-value views**

Allow unique resolved symbols only; disable Add at four and explain the limit. Render normalized prices, selected financial metrics, a sortable table, coverage/source annotations, and an empty state until two companies are present. Removing a company preserves the others and never triggers unrelated refreshes.

- [ ] **Step 5: Run and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_comparison.py tests/test_streamlit_app.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh tests
rtk git add nivesh/services/comparison.py nivesh/ui/app.py nivesh/ui/comparison.py tests
rtk git commit -m "feat: add multi-company comparison"
```

Expected: two-to-four company comparison contracts PASS.

---

### Task 9: Locally bundled Three.js and GSAP financial towers

**Files:**
- Create: `package.json`
- Create: `package-lock.json`
- Create: `component_frontend/src/towers.js`
- Create: `component_frontend/build.mjs`
- Create: `nivesh/components/__init__.py`
- Create: `nivesh/components/financial_towers.py`
- Create: `nivesh/components/assets/towers.html`
- Create: `nivesh/components/assets/towers.css`
- Create: `nivesh/components/assets/towers.js`
- Create: `tests/test_three_component.py`
- Modify: `nivesh/ui/comparison.py`

**Interfaces:**
- Consumes: JSON-safe `ComparisonPayload.towers`.
- Produces: `render_financial_towers(companies, key="financial-towers") -> None`.

- [ ] **Step 1: Pin frontend dependencies and write a failing artifact contract**

Create `package.json` with exact dev dependencies:

```json
{
  "private": true,
  "scripts": {
    "build:component": "node component_frontend/build.mjs"
  },
  "devDependencies": {
    "esbuild": "0.28.2",
    "gsap": "3.15.0",
    "three": "0.185.1"
  }
}
```

Write a test asserting the generated asset contains `export default function`, `WebGLRenderer`, `prefers-reduced-motion`, cleanup calls, and no `http://`, `https://`, or unresolved bare `from "three"` import.

- [ ] **Step 2: Verify the artifact test fails**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_three_component.py -v`

Expected: FAIL because the built component is absent.

- [ ] **Step 3: Implement the readable component source**

`towers.js` imports `three`, `OrbitControls`, and `gsap`; exports the Streamlit Components v2 default mount function; validates the data shape; creates one labelled tower per company; and uses DOM `textContent` for labels/tooltips. It must not assign provider data to `innerHTML`.

Metric buttons switch among `composite`, `quality`, `growth`, `balance_sheet`, and `valuation`. GSAP animates tower `scale.y` and `position.y`; reduced motion sets duration to zero without changing the selected metric. Pointer and keyboard selection expose exact values in a semantic detail panel.

The mount function returns cleanup code that cancels the animation frame, disconnects the resize observer, disposes controls, traverses and disposes geometries/materials/textures, and disposes the renderer.

- [ ] **Step 4: Build a deterministic local browser module**

`build.mjs` calls esbuild with `bundle: true`, `format: "esm"`, `platform: "browser"`, `target: ["es2022"]`, `minify: true`, and the fixed output `nivesh/components/assets/towers.js`. Run `npm ci` after the lock file exists and then `npm run build:component` twice; assert the SHA-256 hash is identical.

- [ ] **Step 5: Register a Streamlit Components v2 wrapper**

```python
_renderer = st.components.v2.component(
    "nivesh_financial_towers",
    html=_asset("towers.html"),
    css=_asset("towers.css"),
    js=_asset("towers.js"),
    isolate_styles=True,
)


def render_financial_towers(companies: list[dict[str, object]], key: str) -> None:
    _renderer(data={"companies": companies}, key=key)
```

The Python wrapper allow-lists fields and validates symbol/name lengths and finite numeric values before mounting trusted component code.

- [ ] **Step 6: Run and commit**

Run:

```powershell
rtk npm ci
rtk npm run build:component
rtk .\.venv\Scripts\python.exe -m pytest tests/test_three_component.py tests/test_comparison.py -v
rtk npm audit
rtk git add package.json package-lock.json component_frontend nivesh/components nivesh/ui/comparison.py tests/test_three_component.py
rtk git commit -m "feat: add interactive financial towers"
```

Expected: deterministic artifact, no external runtime URL, component tests PASS, and npm audit reports no unresolved vulnerability.

---

### Task 10: Dataset-aware caching, targeted refresh, secrets, and data health

**Files:**
- Create: `nivesh/services/loaders.py`
- Create: `.streamlit/secrets.toml.example`
- Test: `tests/test_loaders.py`
- Modify: `nivesh/config.py`
- Modify: `nivesh/ui/app.py`
- Modify: `nivesh/ui/overview.py`

**Interfaces:**
- Consumes: `OpenBBGateway` methods and `AppSettings` TTL values.
- Produces: `load_profile`, `load_prices`, `load_statements`, `load_metrics`, and `clear_symbol_cache`.

- [ ] **Step 1: Write failing targeted-cache tests**

```python
def test_refresh_clears_only_selected_symbol(fake_gateway: CountingGateway) -> None:
    load_prices("RELIANCE.NS", "yfinance", 0)
    load_prices("TCS.NS", "yfinance", 0)
    clear_symbol_cache("RELIANCE.NS", "yfinance")
    load_prices("RELIANCE.NS", "yfinance", 1)
    load_prices("TCS.NS", "yfinance", 0)
    assert fake_gateway.calls["RELIANCE.NS"] == 2
    assert fake_gateway.calls["TCS.NS"] == 1
```

- [ ] **Step 2: Verify failure**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/test_loaders.py -v`

Expected: FAIL because loaders do not exist.

- [ ] **Step 3: Implement cache keys and manual refresh**

Use separate cached functions for prices, profile, statements, and metrics with TTLs 900, 21600, and 86400 seconds. Include resolved symbol, provider, period, and refresh nonce in keys. `clear_symbol_cache` increments only the active symbol's nonce in session state; it does not clear global caches or other symbols.

- [ ] **Step 4: Load optional provider credentials server-side**

Document `[openbb]` keys in `.streamlit/secrets.toml.example` with empty example values. At startup, copy non-empty supported credentials into OpenBB's credential model without logging or returning them. The default yfinance path requires no secret.

- [ ] **Step 5: Surface freshness and partial failures**

The data-health panel groups source date, retrieval time, provider, stale state, coverage, and warnings per dataset. A rate limit or timeout preserves already rendered valid datasets and offers a controlled retry rather than an automatic loop.

- [ ] **Step 6: Run and commit**

Run:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest tests/test_loaders.py tests/test_streamlit_app.py -v
rtk .\.venv\Scripts\ruff.exe check nivesh tests
rtk git add .streamlit/secrets.toml.example nivesh tests/test_loaders.py
rtk git commit -m "feat: add provider-aware freshness controls"
```

Expected: targeted refresh tests PASS and secrets never appear in snapshots or logs.

---

### Task 11: Production packaging, browser verification, and operator documentation

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `README.md`
- Create: `scripts/live_smoke.py`
- Create: `scripts/run_checks.ps1`
- Create: `tests/e2e/test_app.py`
- Modify: `.streamlit/config.toml`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: the complete application.
- Produces: reproducible local, Streamlit Community Cloud, and Docker release paths.

- [ ] **Step 1: Write failing desktop, mobile, reduced-motion, and fallback browser tests**

```python
@pytest.mark.e2e
def test_demo_analysis_and_comparison(page: Page, app_url: str) -> None:
    page.goto(app_url)
    page.get_by_label("NSE or BSE ticker").fill("RELIANCE")
    page.get_by_role("button", name="Analyze").click()
    expect(page.get_by_text("Demo data · not a live provider result")).to_be_visible()
    expect(page.get_by_text("Reliance Industries Limited")).to_be_visible()
    page.get_by_role("button", name="Add RELIANCE.NS to comparison").click()
    page.get_by_label("NSE or BSE ticker").fill("TCS")
    page.get_by_role("button", name="Analyze").click()
    page.get_by_role("button", name="Add TCS.NS to comparison").click()
    page.get_by_role("tab", name="Compare").click()
    expect(page.locator("[data-testid='financial-towers'] canvas")).to_be_visible()


@pytest.mark.e2e
def test_mobile_has_no_horizontal_page_overflow(page: Page, app_url: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(app_url)
    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    assert overflow is False
```

Add tests that emulate `prefers-reduced-motion: reduce`, replace `WebGLRenderingContext` with `undefined`, and fail on uncaught page errors or console error messages.

- [ ] **Step 2: Verify browser tests fail before the harness exists**

Run: `rtk .\.venv\Scripts\python.exe -m pytest tests/e2e/test_app.py -m e2e -v`

Expected: FAIL because the app server fixture and stable test IDs are not complete.

- [ ] **Step 3: Add the production container and Streamlit settings**

Use `python:3.11-slim`, install `requirements.txt`, run as a non-root user, expose port 8501, add a health check against `/_stcore/health`, and start `streamlit run app.py --server.address=0.0.0.0`. Exclude `.git`, `.venv`, tests, local secrets, caches, and Node modules from the Docker context.

- [ ] **Step 4: Add the release gate script**

`scripts/run_checks.ps1` stops at the first failure and runs:

```powershell
rtk .\.venv\Scripts\python.exe -m pytest -m "not live and not e2e" -q
rtk .\.venv\Scripts\ruff.exe check app.py nivesh scripts tests
rtk .\.venv\Scripts\mypy.exe nivesh
rtk .\.venv\Scripts\pip-audit.exe -r requirements.txt
rtk npm ci
rtk npm run build:component
rtk npm audit
rtk git diff --check
```

The script then starts Streamlit in demo mode on a free local port, waits for `/_stcore/health`, runs the e2e suite against desktop and mobile viewports, and terminates only the process it started.

- [ ] **Step 5: Document setup, methodology, limits, and deployment**

README sections must cover Python 3.11 setup, `streamlit run app.py`, explicit demo mode, free-provider limitations, optional secret names, score formulas and thresholds, data freshness, Streamlit Community Cloud steps, Docker build/run commands, health endpoint, live smoke test, troubleshooting, provider terms, and the statement that Nivesh is research support rather than investment advice.

- [ ] **Step 6: Run the bounded live smoke check**

Run: `rtk .\.venv\Scripts\python.exe scripts/live_smoke.py --symbol RELIANCE.NS --timeout 45`

Expected: exit 0 when at least one dataset is returned; otherwise exit 2 with provider/date/warning diagnostics and no false application success claim.

- [ ] **Step 7: Run the full release gate and inspect both viewports**

Run: `rtk powershell -ExecutionPolicy Bypass -File scripts/run_checks.ps1`

Expected: unit/AppTest/e2e tests PASS, lint/type/dependency checks PASS, component build is deterministic, desktop and 390-by-844 workflows have no console errors, and `git diff --check` is clean.

- [ ] **Step 8: Commit the production-ready application**

Run:

```powershell
rtk git add .dockerignore Dockerfile README.md .streamlit pyproject.toml scripts tests/e2e
rtk git commit -m "chore: harden Nivesh for production"
rtk git status --short
```

Expected: final commit succeeds and status is clean. Do not deploy unless the user separately requests deployment.

---

## Final verification checklist

- [ ] `RELIANCE`, `RELIANCE.NS`, and `500325.BO` resolve correctly; malicious input is rejected.
- [ ] OpenBB free-provider calls return data or precise provider-limited warnings.
- [ ] Missing metrics render as `—` and never affect scores as zero.
- [ ] Annual and quarterly periods remain correctly aligned.
- [ ] Score methodology, weights, exclusions, periods, and coverage are visible.
- [ ] Two to four companies compare correctly in charts, tables, and towers.
- [ ] Three.js and GSAP are locally bundled at pinned versions.
- [ ] Reduced motion changes animation intensity/duration, not content state.
- [ ] WebGL failure leaves the analytical comparison usable.
- [ ] Desktop and 390-by-844 workflows pass without uncaught browser errors.
- [ ] Runtime, frontend, lint, type, test, and dependency-audit gates pass.
- [ ] No secret, local cache, or virtual environment is tracked.
- [ ] No deployment occurs without explicit authorization.
