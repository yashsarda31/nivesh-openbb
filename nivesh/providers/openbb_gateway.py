"""Resilient OpenBB adapter with dataset-level provenance and failures."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from typing import Any

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


class OpenBBGateway:
    """Translate OpenBB outputs into stable provider-neutral contracts."""

    def __init__(self, client: Any, provider: str = "yfinance") -> None:
        self.client = client
        self.provider = provider

    @classmethod
    def from_openbb(cls, provider: str = "yfinance") -> OpenBBGateway:
        """Construct the gateway lazily so unit tests do not import OpenBB."""

        from openbb import obb

        return cls(client=obb, provider=provider)

    def _fetch_records(
        self,
        route_name: str,
        route: Callable[..., Any],
        **kwargs: object,
    ) -> DatasetResult[list[dict[str, Any]]]:
        retrieved_at = datetime.now(UTC)
        try:
            output = route(provider=self.provider, **kwargs)
            records = [
                item.model_dump(exclude_none=False)
                for item in (getattr(output, "results", None) or [])
            ]
            provider = str(getattr(output, "provider", None) or self.provider)
            warnings = tuple(self._warning_text(item) for item in (output.warnings or []))
            return DatasetResult(
                data=records,
                provider=provider,
                retrieved_at=retrieved_at,
                as_of=self._records_as_of(records),
                warnings=warnings,
                coverage=1.0 if records else 0.0,
            )
        except Exception as exc:  # Provider packages expose multiple exception types.
            return DatasetResult(
                data=[],
                provider=self.provider,
                retrieved_at=retrieved_at,
                warnings=(f"{route_name}: {exc}",),
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
        profile = CompanyProfile(
            symbol=str(record.get("symbol") or symbol),
            name=self._optional_text(record.get("name")),
            exchange=self._optional_text(record.get("exchange")),
            sector=self._optional_text(record.get("sector")),
            industry=self._optional_text(record.get("industry")),
            currency=self._optional_text(record.get("currency")),
            market_cap=self._optional_float(record.get("market_cap")),
            website=self._optional_text(record.get("website")),
            description=self._optional_text(
                record.get("company_description") or record.get("description")
            ),
        )
        return DatasetResult(
            data=profile,
            provider=raw.provider,
            retrieved_at=raw.retrieved_at,
            as_of=raw.as_of or raw.retrieved_at.date(),
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

        common = {"symbol": symbol, "period": period, "limit": 8}
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
            period=period,
            limit=8,
            ttm="exclude",
        )
        record = raw.data[-1] if raw.data else {}
        metrics = {
            key: self._optional_float(value)
            for key, value in record.items()
            if key not in _METRIC_METADATA and (value is None or isinstance(value, int | float))
        }
        return DatasetResult(
            data=metrics,
            provider=raw.provider,
            retrieved_at=raw.retrieved_at,
            as_of=raw.as_of,
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
