"""Typed contracts that keep provider metadata beside financial data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class DatasetResult(BaseModel, Generic[T]):
    """A normalized dataset together with provenance and completeness metadata."""

    model_config = ConfigDict(frozen=True)

    data: T
    provider: str
    retrieved_at: datetime
    as_of: date | datetime | None = None
    period: str | None = None
    currency: str | None = None
    stale: bool = False
    warnings: tuple[str, ...] = ()
    coverage: float = Field(default=1.0, ge=0.0, le=1.0)


class CompanyProfile(BaseModel):
    """Provider-neutral company identity and classification."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    market_cap: float | None = None
    website: str | None = None
    description: str | None = None


class PricePoint(BaseModel):
    """One exact historical price observation."""

    model_config = ConfigDict(frozen=True)

    date: date | datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: float | None = None


class FinancialPeriod(BaseModel):
    """Aligned financial statement values for one reporting period."""

    model_config = ConfigDict(frozen=True)

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


class MetricScore(BaseModel):
    """One inspectable score input and its transformation result."""

    model_config = ConfigDict(frozen=True)

    name: str
    label: str
    raw_value: float | None = None
    score: float | None = Field(default=None, ge=0.0, le=100.0)
    effective_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    direction: Literal["higher", "lower"]
    source_period: str | None = None
    excluded_reason: str | None = None


class ComponentScore(BaseModel):
    """A score component with explicit coverage and excluded inputs."""

    model_config = ConfigDict(frozen=True)

    name: str
    score: int | None = Field(default=None, ge=0, le=100)
    coverage: float = Field(ge=0.0, le=1.0)
    target_weight: float = Field(ge=0.0, le=1.0)
    metrics: dict[str, MetricScore] = Field(default_factory=dict)
    excluded: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class Scorecard(BaseModel):
    """Composite research score with deterministic coverage rules."""

    model_config = ConfigDict(frozen=True)

    composite: int | None = Field(default=None, ge=0, le=100)
    coverage: float = Field(ge=0.0, le=1.0)
    components: dict[str, ComponentScore]
    methodology_version: str = "nivesh-v1"
    warnings: tuple[str, ...] = ()


class AnalysisBundle(BaseModel):
    """All normalized datasets required by a single-company workspace."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    profile: DatasetResult[CompanyProfile]
    prices: DatasetResult[list[PricePoint]]
    statements: DatasetResult[list[FinancialPeriod]]
    metrics: DatasetResult[dict[str, float | None]]
    scorecard: Scorecard | None = None


class StatementDatasets(BaseModel):
    """Raw statement datasets kept separate so one provider failure is isolated."""

    model_config = ConfigDict(frozen=True)

    income: DatasetResult[list[dict[str, Any]]]
    balance: DatasetResult[list[dict[str, Any]]]
    cash: DatasetResult[list[dict[str, Any]]]


class ProviderBundle(BaseModel):
    """Provider responses ready for normalization into an analysis bundle."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    profile: DatasetResult[CompanyProfile]
    prices: DatasetResult[list[PricePoint]]
    statements: StatementDatasets
    metrics: DatasetResult[dict[str, float | None]]
