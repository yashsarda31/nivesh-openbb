from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

PROFILE = [
    {
        "symbol": "RELIANCE.NS",
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "sector": "Energy",
        "industry": "Oil & Gas Integrated",
        "currency": "INR",
        "market_cap": None,
        "website": "https://www.ril.com",
        "company_description": "Diversified energy and consumer company.",
    }
]

PRICES = [
    {
        "date": "2026-08-20",
        "open": 1_380.0,
        "high": 1_405.0,
        "low": 1_375.0,
        "close": 1_400.0,
        "volume": 8_000_000,
    },
    {
        "date": "2026-08-21",
        "open": 1_401.0,
        "high": 1_415.0,
        "low": 1_392.0,
        "close": 1_410.0,
        "volume": 7_500_000,
    },
]

INCOME = [
    {"period_ending": "2024-03-31", "fiscal_year": 2024, "revenue": 900.0, "net_income": 70.0},
    {"period_ending": "2025-03-31", "fiscal_year": 2025, "revenue": 1_000.0, "net_income": 80.0},
]

BALANCE = [
    {
        "period_ending": "2024-03-31",
        "fiscal_year": 2024,
        "total_assets": 2_000.0,
        "total_equity": 900.0,
        "total_debt": 420.0,
    },
    {
        "period_ending": "2025-03-31",
        "fiscal_year": 2025,
        "total_assets": 2_100.0,
        "total_equity": 1_000.0,
        "total_debt": 400.0,
    },
]

CASH = [
    {
        "period_ending": "2024-03-31",
        "fiscal_year": 2024,
        "operating_cash_flow": 100.0,
        "capital_expenditure": -45.0,
    },
    {
        "period_ending": "2025-03-31",
        "fiscal_year": 2025,
        "operating_cash_flow": 120.0,
        "capital_expenditure": -50.0,
    },
]

METRICS = [{"period_ending": "2025-03-31", "pe_ratio": 24.0, "price_to_book": None}]


class FakeItem:
    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def model_dump(self, *, exclude_none: bool = False) -> dict[str, Any]:
        if exclude_none:
            return {key: value for key, value in self.values.items() if value is not None}
        return dict(self.values)


class FakeOutput:
    def __init__(self, rows: list[dict[str, Any]], provider: str = "yfinance") -> None:
        self.results = [FakeItem(row) for row in rows]
        self.provider = provider
        self.warnings = []


class FakeRoute:
    def __init__(self, name: str, owner: FakeOBB) -> None:
        self.name = name
        self.owner = owner

    def __call__(self, **kwargs: Any) -> FakeOutput:
        self.owner.calls.append((self.name, kwargs))
        if self.name in self.owner.raise_on:
            raise RuntimeError(f"{self.name} provider unavailable")
        return FakeOutput(self.owner.payloads[self.name])


class FakeOBB:
    def __init__(self) -> None:
        self.raise_on: set[str] = set()
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.payloads = {
            "profile": PROFILE,
            "prices": PRICES,
            "income": INCOME,
            "balance": BALANCE,
            "cash": CASH,
            "metrics": METRICS,
        }
        self.equity = SimpleNamespace(
            profile=FakeRoute("profile", self),
            price=SimpleNamespace(historical=FakeRoute("prices", self)),
            fundamental=SimpleNamespace(
                income=FakeRoute("income", self),
                balance=FakeRoute("balance", self),
                cash=FakeRoute("cash", self),
                metrics=FakeRoute("metrics", self),
            ),
        )


GatewayFactory = Callable[[FakeOBB], object]
