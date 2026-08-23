from datetime import UTC, date, datetime

from nivesh.config import AppSettings
from nivesh.domain.models import (
    AnalysisBundle,
    CompanyProfile,
    ComponentScore,
    DatasetResult,
    FinancialPeriod,
    PricePoint,
    Scorecard,
)


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


def test_settings_parse_environment_style_values() -> None:
    settings = AppSettings.from_mapping(
        {
            "NIVESH_PROVIDER": "fmp",
            "NIVESH_DEMO_MODE": "yes",
            "NIVESH_PRICE_TTL": "120",
            "NIVESH_PROFILE_TTL": "600",
            "NIVESH_STATEMENT_TTL": "3600",
        }
    )

    assert settings.provider == "fmp"
    assert settings.demo_mode is True
    assert settings.profile_ttl_seconds == 600
    assert settings.statement_ttl_seconds == 3600


def test_analysis_bundle_keeps_typed_empty_datasets() -> None:
    retrieved_at = datetime.now(UTC)
    profile = DatasetResult(
        data=CompanyProfile(symbol="RELIANCE.NS", name="Reliance Industries Limited"),
        provider="fixture",
        retrieved_at=retrieved_at,
    )
    bundle = AnalysisBundle(
        symbol="RELIANCE.NS",
        profile=profile,
        prices=DatasetResult[list[PricePoint]](
            data=[], provider="fixture", retrieved_at=retrieved_at, coverage=0.0
        ),
        statements=DatasetResult[list[FinancialPeriod]](
            data=[FinancialPeriod(period_ending=date(2025, 3, 31), total_debt=0.0)],
            provider="fixture",
            retrieved_at=retrieved_at,
        ),
        metrics=DatasetResult[dict[str, float | None]](
            data={"pe_ratio": None},
            provider="fixture",
            retrieved_at=retrieved_at,
            coverage=0.0,
        ),
    )

    assert bundle.prices.data == []
    assert bundle.statements.data[0].total_debt == 0.0
    assert bundle.metrics.data["pe_ratio"] is None


def test_scorecard_allows_withheld_composite() -> None:
    scorecard = Scorecard(
        composite=None,
        coverage=0.45,
        components={
            "quality": ComponentScore(
                name="quality", score=None, coverage=0.4, target_weight=0.25
            )
        },
    )

    assert scorecard.composite is None
    assert scorecard.components["quality"].coverage == 0.4
