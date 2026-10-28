"""Assemble normalized provider or demo data into one analysis contract."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from nivesh.domain.models import (
    AnalysisBundle,
    CompanyProfile,
    DatasetResult,
    FinancialPeriod,
    PricePoint,
    ProviderBundle,
)
from nivesh.providers.openbb_gateway import OpenBBGateway
from nivesh.services.freshness import assess_bundle_freshness
from nivesh.services.normalization import enrich_periods, normalize_statements
from nivesh.services.scoring import score_company

_DEMO_DIR = Path(__file__).parents[1] / "assets" / "demo"


class DemoFixture(BaseModel):
    """Validated shape of a visibly labelled offline demonstration fixture."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    profile: CompanyProfile
    prices: list[PricePoint]
    annual_statements: list[FinancialPeriod]
    quarterly_statements: list[FinancialPeriod]
    metrics: dict[str, float | None]
    as_of: date


class DemoSymbolUnavailableError(ValueError):
    """Raised when explicit demo mode has no fixture for a requested company."""


def load_demo_analysis(symbol: str, period: str) -> AnalysisBundle:
    """Load a versioned demo fixture without substituting a different company."""

    path = _DEMO_DIR / f"{symbol}.json"
    if not path.is_file():
        raise DemoSymbolUnavailableError(
            f"{symbol} is not included in demo data. Try RELIANCE or TCS."
        )
    fixture = DemoFixture.model_validate(json.loads(path.read_text(encoding="utf-8")))
    periods = fixture.annual_statements if period == "annual" else fixture.quarterly_statements
    enriched = enrich_periods(periods, frequency=period)
    retrieved_at = datetime.now(UTC)
    warning = "Demo fixture; not a live provider result."
    scorecard = score_company(
        enriched,
        fixture.metrics,
        sector=fixture.profile.sector,
        frequency=period,
    )
    result = AnalysisBundle(
        symbol=fixture.symbol,
        profile=DatasetResult(
            data=fixture.profile,
            provider="demo",
            retrieved_at=retrieved_at,
            as_of=fixture.as_of,
            currency=fixture.profile.currency,
            warnings=(warning,),
        ),
        prices=DatasetResult(
            data=fixture.prices,
            provider="demo",
            retrieved_at=retrieved_at,
            as_of=max((point.date for point in fixture.prices), default=fixture.as_of),
            currency=fixture.profile.currency,
            warnings=(warning,),
        ),
        statements=DatasetResult(
            data=enriched,
            provider="demo",
            retrieved_at=retrieved_at,
            as_of=max((item.period_ending for item in enriched), default=fixture.as_of),
            period=period,
            currency=fixture.profile.currency,
            warnings=(warning,),
        ),
        metrics=DatasetResult(
            data=fixture.metrics,
            provider="demo",
            retrieved_at=retrieved_at,
            as_of=fixture.as_of,
            period=period,
            currency=fixture.profile.currency,
            warnings=(warning,),
        ),
        scorecard=scorecard,
    )
    return assess_bundle_freshness(result)


def fetch_live_analysis(symbol: str, period: str, provider: str) -> AnalysisBundle:
    """Fetch and assemble live OpenBB datasets while retaining partial failures."""

    gateway = OpenBBGateway.from_openbb(provider=provider)
    return assemble_provider_bundle(gateway.fetch_provider_bundle(symbol, period), period)


def assemble_provider_bundle(bundle: ProviderBundle, period: str) -> AnalysisBundle:
    """Normalize a provider bundle into the UI-facing analysis contract."""

    statements = bundle.statements
    periods = enrich_periods(
        normalize_statements(
            statements.income.data,
            statements.balance.data,
            statements.cash.data,
        ),
        frequency=period,
    )
    statement_results = (statements.income, statements.balance, statements.cash)
    statement_warnings = tuple(
        warning for result in statement_results for warning in result.warnings
    )
    providers = sorted({result.provider for result in statement_results})
    statement_provider = ", ".join(providers) if providers else "unknown"
    retrieved_at = max(result.retrieved_at for result in statement_results)
    statement_coverage = sum(result.coverage for result in statement_results) / 3
    currency = next((item.currency for item in periods if item.currency), None)
    profile = bundle.profile.data

    normalized_statements = DatasetResult(
        data=periods,
        provider=statement_provider,
        retrieved_at=retrieved_at,
        as_of=max((item.period_ending for item in periods), default=None),
        period=period,
        currency=currency,
        warnings=statement_warnings,
        coverage=statement_coverage,
    )
    result = AnalysisBundle(
        symbol=bundle.symbol,
        profile=bundle.profile,
        prices=bundle.prices,
        statements=normalized_statements,
        metrics=bundle.metrics,
        scorecard=score_company(
            periods, bundle.metrics.data, sector=profile.sector, frequency=period
        ),
    )
    return assess_bundle_freshness(result)


def demo_symbols() -> tuple[str, ...]:
    """Return the explicit demo catalog for user-facing guidance."""

    return tuple(path.stem for path in sorted(_DEMO_DIR.glob("*.json")))
