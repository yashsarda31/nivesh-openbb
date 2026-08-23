import builtins
from datetime import date

from nivesh.providers.openbb_gateway import OpenBBGateway, _ProviderClient
from tests.fixtures.openbb_payloads import FakeItem, FakeOBB


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        return [FakeItem({"symbol": "TCS.NS"})]


def test_gateway_construction_does_not_import_generated_openbb_sdk(
    monkeypatch,
) -> None:
    """The deployed runtime must not trigger OpenBB's site-packages build."""

    original_import = builtins.__import__

    def reject_generated_sdk(name, *args, **kwargs):
        if name == "openbb":
            raise PermissionError("read-only site-packages/openbb/.build.lock")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_generated_sdk)

    gateway = OpenBBGateway.from_openbb(provider="yfinance")

    assert gateway.provider == "yfinance"


def test_provider_client_executes_openbb_fetcher_without_static_sdk() -> None:
    executor = RecordingExecutor()
    credentials = {}
    client = _ProviderClient(executor, credentials)
    credentials["fmp_api_key"] = "added-after-client-construction"

    output = client.equity.profile(provider="yfinance", symbol="TCS.NS")

    assert output.results[0].model_dump()["symbol"] == "TCS.NS"
    assert executor.calls == [
        {
            "provider_name": "yfinance",
            "model_name": "EquityInfo",
            "params": {"symbol": "TCS.NS"},
            "credentials": {"fmp_api_key": "added-after-client-construction"},
        }
    ]


def test_profile_maps_provider_and_preserves_missing() -> None:
    gateway = OpenBBGateway(client=FakeOBB(), provider="yfinance")

    result = gateway.fetch_profile("RELIANCE.NS")

    assert result.provider == "yfinance"
    assert result.data.name == "Reliance Industries Limited"
    assert result.data.market_cap is None
    assert result.as_of is not None


def test_prices_are_typed_and_keep_provider_date() -> None:
    gateway = OpenBBGateway(client=FakeOBB(), provider="yfinance")

    result = gateway.fetch_prices("RELIANCE.NS", start_date=date(2026, 8, 1))

    assert result.data[-1].close == 1_410.0
    assert result.as_of == date(2026, 8, 21)
    assert result.coverage == 1.0


def test_statement_failure_does_not_discard_prices() -> None:
    client = FakeOBB()
    client.raise_on.add("income")
    gateway = OpenBBGateway(client=client, provider="yfinance")

    bundle = gateway.fetch_provider_bundle("RELIANCE.NS", period="annual")

    assert bundle.prices.data
    assert bundle.statements.income.data == []
    assert "income provider unavailable" in " ".join(bundle.statements.income.warnings)
    assert bundle.statements.balance.data


def test_metrics_keep_unavailable_values_as_none() -> None:
    gateway = OpenBBGateway(client=FakeOBB(), provider="yfinance")

    result = gateway.fetch_metrics("RELIANCE.NS", period="annual")

    assert result.data["pe_ratio"] == 24.0
    assert result.data["price_to_book"] is None
