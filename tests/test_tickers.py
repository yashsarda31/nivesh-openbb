from datetime import date
from pathlib import Path

import pytest

from nivesh.services.tickers import (
    SymbolValidationError,
    parse_nse_symbol_master,
    resolve_symbol,
    search_symbols,
    serialize_symbol_catalog,
)


@pytest.mark.parametrize(
    ("raw", "expected", "exchange"),
    [
        ("reliance", "RELIANCE.NS", "NSE"),
        ("M&M.NS", "M&M.NS", "NSE"),
        ("500325.bo", "500325.BO", "BSE"),
        ("BAJAJ-AUTO", "BAJAJ-AUTO.NS", "NSE"),
    ],
)
def test_resolve_symbol(raw: str, expected: str, exchange: str) -> None:
    resolved = resolve_symbol(raw)

    assert resolved.symbol == expected
    assert resolved.exchange == exchange


@pytest.mark.parametrize("raw", ["", "../../etc", "RELIANCE<script>", "A" * 31])
def test_rejects_unsafe_symbols(raw: str) -> None:
    with pytest.raises(SymbolValidationError):
        resolve_symbol(raw)


def test_parse_nse_master_keeps_only_equity_series() -> None:
    csv_text = Path("tests/fixtures/EQUITY_L_sample.csv").read_text(encoding="utf-8")
    records = parse_nse_symbol_master(csv_text, as_of=date(2026, 8, 24))

    assert [record.symbol for record in records] == ["RELIANCE.NS", "TCS.NS"]
    assert records[0].name == "Reliance Industries Limited"
    assert records[0].snapshot_date == date(2026, 8, 24)


def test_parse_nse_master_accepts_current_spaced_headers() -> None:
    csv_text = (
        "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING\n"
        "RELIANCE,Reliance Industries Limited,EQ,29-NOV-1995\n"
    )

    records = parse_nse_symbol_master(csv_text, as_of=date(2026, 8, 24))

    assert records[0].symbol == "RELIANCE.NS"


def test_search_ranks_exact_then_symbol_prefix_then_company_name() -> None:
    csv_text = Path("tests/fixtures/EQUITY_L_sample.csv").read_text(encoding="utf-8")
    records = parse_nse_symbol_master(csv_text, as_of=date(2026, 8, 24))

    assert search_symbols("TCS", records)[0].symbol == "TCS.NS"
    assert search_symbols("rel", records)[0].symbol == "RELIANCE.NS"
    assert search_symbols("consultancy", records)[0].symbol == "TCS.NS"


def test_serialize_symbol_catalog_is_stable() -> None:
    csv_text = Path("tests/fixtures/EQUITY_L_sample.csv").read_text(encoding="utf-8")
    records = parse_nse_symbol_master(csv_text, as_of=date(2026, 8, 24))

    rendered = serialize_symbol_catalog(records)

    assert rendered.splitlines()[0] == "symbol,name,exchange,snapshot_date"
    assert "RELIANCE.NS,Reliance Industries Limited,NSE,2026-08-24" in rendered
