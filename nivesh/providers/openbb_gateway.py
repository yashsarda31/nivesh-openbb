"""Resilient OpenBB adapter with dataset-level provenance and failures."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from time import sleep
from types import SimpleNamespace
from typing import Any
from warnings import catch_warnings, simplefilter

from nivesh.domain.models import (
    CompanyProfile,
    DatasetResult,
    PricePoint,
    ProviderBundle,
    StatementDatasets,
)

_METRIC_METADATA = {
    "period_ending",
    "fiscal_period",
    "fiscal_year",
    "reported_currency",
    "symbol",
}
_RUNTIME_CREDENTIALS: dict[str, Any] = {}


def set_runtime_credentials(credentials: Mapping[str, str]) -> None:
    """Update credentials consumed by the provider executor without importing the SDK."""

    from pydantic import SecretStr

    for key, value in credentials.items():
        _RUNTIME_CREDENTIALS[key] = SecretStr(value)


@dataclass(frozen=True)
class _ExecutorOutput:
    results: list[Any]
    provider: str
    warnings: tuple[str, ...]


class _ExecutorRoute:
    def __init__(self, executor: Any, model_name: str, credentials: Mapping[str, Any]) -> None:
        self._executor = executor
        self._model_name = model_name
        self._credentials = credentials

    def __call__(self, *, provider: str, **params: object) -> _ExecutorOutput:
        from openbb_core.provider.utils.helpers import run_async

        with catch_warnings(record=True) as caught:
            simplefilter("always")
            result = run_async(
                self._executor.execute,
                provider_name=provider,
                model_name=self._model_name,
                params=dict(params),
                credentials=dict(self._credentials),
            )
        rows = getattr(result, "result", result)
        if rows is None:
            normalized_rows: list[Any] = []
        elif isinstance(rows, list):
            normalized_rows = rows
        else:
            normalized_rows = [rows]
        return _ExecutorOutput(
            results=normalized_rows,
            provider=provider,
            warnings=tuple(str(item.message) for item in caught),
        )


class _ProviderClient:
    """OpenBB provider routes without the generated, self-writing SDK package."""

    def __init__(self, executor: Any, credentials: Mapping[str, Any] | None = None) -> None:
        shared_credentials = credentials if credentials is not None else {}

        def route(model_name: str) -> _ExecutorRoute:
            return _ExecutorRoute(executor, model_name, shared_credentials)

        self.equity = SimpleNamespace(
            profile=route("EquityInfo"),
            price=SimpleNamespace(historical=route("EquityHistorical")),
            fundamental=SimpleNamespace(
                income=route("IncomeStatement"),
                balance=route("BalanceSheet"),
                cash=route("CashFlowStatement"),
                metrics=route("KeyMetrics"),
            ),
        )

    @classmethod
    def from_extensions(cls) -> _ProviderClient:
        from openbb_core.provider.query_executor import QueryExecutor

        return cls(QueryExecutor(), _RUNTIME_CREDENTIALS)


class OpenBBGateway:
    """Translate OpenBB outputs into stable provider-neutral contracts."""

    def __init__(
        self,
        client: Any,
        provider: str = "yfinance",
        *,
        max_retries: int = 1,
        retry_backoff_seconds: float = 1.5,
    ) -> None:
        self.client = client
        self.provider = provider
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    @classmethod
    def from_openbb(
        cls,
        provider: str = "yfinance",
        *,
        max_retries: int = 1,
        retry_backoff_seconds: float = 1.5,
    ) -> OpenBBGateway:
        """Construct from OpenBB providers without generating files at runtime."""

        return cls(
            client=_ProviderClient.from_extensions(),
            provider=provider,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )

    def _fetch_records(
        self,
        route_name: str,
        route: Callable[..., Any],
        **kwargs: object,
    ) -> DatasetResult[list[dict[str, Any]]]:
        """Fetch one route with bounded retries for transient provider failures."""

        retrieved_at = datetime.now(UTC)
        attempts = self.max_retries + 1
        collected: list[str] = []
        for attempt in range(1, attempts + 1):
            try:
                output = route(provider=self.provider, **kwargs)
                records = [
                    item.model_dump(exclude_none=False)
                    for item in (getattr(output, "results", None) or [])
                ]
            except Exception as exc:  # Provider packages expose multiple exception types.
                collected.append(f"{route_name}: {exc}")
                if attempt < attempts:
                    sleep(self.retry_backoff_seconds * attempt)
                    continue
                return DatasetResult(
                    data=[],
                    provider=self.provider,
                    retrieved_at=retrieved_at,
                    warnings=tuple(collected),
                    coverage=0.0,
                )
            if not records and attempt < attempts:
                # Rate-limited providers sometimes answer with silent empty payloads.
                sleep(self.retry_backoff_seconds * attempt)
                continue
            provider = str(getattr(output, "provider", None) or self.provider)
            warnings = tuple(self._warning_text(item) for item in (output.warnings or []))
            return DatasetResult(
                data=records,
                provider=provider,
                retrieved_at=retrieved_at,
                as_of=self._records_as_of(records),
                warnings=tuple(collected) + warnings,
                coverage=1.0 if records else 0.0,
            )
        return DatasetResult(
            data=[],
            provider=self.provider,
            retrieved_at=retrieved_at,
            warnings=tuple(collected),
            coverage=0.0,
        )

    @staticmethod
    def _warning_text(warning: object) -> str:
        if hasattr(warning, "model_dump"):
            return str(warning.model_dump())
        return str(warning)

    @classmethod
    def _records_as_of(cls, records: list[dict[str, Any]]) -> date | None:
        dates = [
            parsed
            for record in records
            for candidate in (record.get("date"), record.get("period_ending"))
            if (parsed := cls._as_date(candidate)) is not None
        ]
        return max(dates, default=None)

    @staticmethod
    def _as_date(value: object) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    def fetch_profile(self, symbol: str) -> DatasetResult[CompanyProfile]:
        """Fetch a company profile while preserving unavailable fields."""

        raw = self._fetch_records("profile", self.client.equity.profile, symbol=symbol)
        record = raw.data[0] if raw.data else {}

        def first_text(*keys: str) -> str | None:
            """Return the first available provider key, honoring naming variants."""

            for key in keys:
                if (text := self._optional_text(record.get(key))) is not None:
                    return text
            return None

        profile = CompanyProfile(
            symbol=str(record.get("symbol") or symbol),
            name=first_text("name"),
            exchange=first_text("exchange", "stock_exchange"),
            sector=first_text("sector", "sector_category"),
            # openbb-yfinance names these industry_category / long_description.
            industry=first_text("industry", "industry_category"),
            currency=first_text("currency"),
            market_cap=self._optional_float(record.get("market_cap")),
            website=first_text("website", "company_url"),
            description=first_text("company_description", "description", "long_description"),
        )
        return DatasetResult(
            data=profile,
            provider=raw.provider,
            retrieved_at=raw.retrieved_at,
            as_of=raw.as_of,
            currency=profile.currency,
            warnings=raw.warnings,
            coverage=raw.coverage,
        )

    def fetch_prices(self, symbol: str, start_date: date) -> DatasetResult[list[PricePoint]]:
        """Fetch daily price history with exact close values."""

        raw = self._fetch_records(
            "prices",
            self.client.equity.price.historical,
            symbol=symbol,
            start_date=start_date,
            interval="1d",
        )
        points = [
            PricePoint(
                date=record["date"],
                open=self._optional_float(record.get("open")),
                high=self._optional_float(record.get("high")),
                low=self._optional_float(record.get("low")),
                close=float(record["close"]),
                volume=self._optional_float(record.get("volume")),
            )
            for record in raw.data
            if record.get("date") is not None
            and self._optional_float(record.get("close")) is not None
        ]
        price_dates = [
            point.date.date() if isinstance(point.date, datetime) else point.date
            for point in points
        ]
        return DatasetResult(
            data=points,
            provider=raw.provider,
            retrieved_at=raw.retrieved_at,
            as_of=max(price_dates, default=None),
            warnings=raw.warnings,
            coverage=1.0 if points else 0.0,
        )

    def fetch_statements(self, symbol: str, period: str) -> StatementDatasets:
        """Fetch the three statements independently for partial rendering."""

        # openbb-yfinance caps the three statement models at limit<=5 (pydantic
        # le=5). Sending limit=8 raises ValidationError before reaching yfinance.
        provider_period = "quarter" if period == "quarterly" else period
        common = {"symbol": symbol, "period": provider_period, "limit": 5}
        fundamental = self.client.equity.fundamental
        return StatementDatasets(
            income=self._fetch_records("income", fundamental.income, **common),
            balance=self._fetch_records("balance", fundamental.balance, **common),
            cash=self._fetch_records("cash", fundamental.cash, **common),
        )

    def fetch_metrics(self, symbol: str, period: str) -> DatasetResult[dict[str, float | None]]:
        """Fetch the latest supported metrics without coercing absent fields."""

        raw = self._fetch_records(
            "metrics",
            self.client.equity.fundamental.metrics,
            symbol=symbol,
            period="quarter" if period == "quarterly" else period,
            limit=8,
            ttm="exclude",
        )
        record = max(
            raw.data,
            key=lambda row: self._records_as_of([row]) or date.min,
            default={},
        )
        metrics = {
            key: self._optional_float(value)
            for key, value in record.items()
            if key not in _METRIC_METADATA and (value is None or isinstance(value, int | float))
        }
        # Yahoo's debtToEquity snapshot is percentage-style; preserve its raw
        # field but provide an unambiguous ratio for every downstream consumer.
        yahoo_debt = metrics.get("debt_to_equity")
        if self.provider == "yfinance" and yahoo_debt is not None:
            metrics["debt_equity"] = yahoo_debt / 100.0
        return DatasetResult(
            data=metrics,
            provider=raw.provider,
            retrieved_at=raw.retrieved_at,
            as_of=self._records_as_of([record]),
            period=period,
            warnings=raw.warnings,
            coverage=raw.coverage,
        )

    def fetch_provider_bundle(self, symbol: str, period: str) -> ProviderBundle:
        """Fetch all datasets while keeping each route's success independent."""

        return ProviderBundle(
            symbol=symbol,
            profile=self.fetch_profile(symbol),
            prices=self.fetch_prices(symbol, start_date=date.today() - timedelta(days=365 * 5)),
            statements=self.fetch_statements(symbol, period),
            metrics=self.fetch_metrics(symbol, period),
        )

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return str(value) if value not in {None, ""} else None

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            number = float(value)
        elif isinstance(value, str):
            try:
                number = float(value)
            except ValueError:
                return None
        else:
            return None
        return number if isfinite(number) else None
