"""Validation and search helpers for Indian exchange symbols."""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from io import StringIO

_BARE = re.compile(r"^[A-Z0-9&-]{1,20}$")
_NSE = re.compile(r"^[A-Z0-9&-]{1,20}\.NS$")
_BSE = re.compile(r"^[0-9]{6}\.BO$")
_NSE_COLUMNS = {"SYMBOL", "NAME OF COMPANY", "SERIES"}


class SymbolValidationError(ValueError):
    """Raised when a user-supplied symbol is unsupported or unsafe."""


@dataclass(frozen=True, slots=True)
class ResolvedTicker:
    """A normalized provider symbol and its exchange."""

    symbol: str
    exchange: str
    original: str


@dataclass(frozen=True, slots=True)
class SymbolRecord:
    """One versioned row in the Indian equity search catalog."""

    symbol: str
    name: str
    exchange: str
    snapshot_date: date


def resolve_symbol(raw: str) -> ResolvedTicker:
    """Normalize a bare NSE symbol or validate an explicit NSE/BSE symbol."""

    value = raw.strip().upper()
    if _NSE.fullmatch(value):
        return ResolvedTicker(symbol=value, exchange="NSE", original=raw)
    if _BSE.fullmatch(value):
        return ResolvedTicker(symbol=value, exchange="BSE", original=raw)
    if _BARE.fullmatch(value):
        return ResolvedTicker(symbol=f"{value}.NS", exchange="NSE", original=raw)
    raise SymbolValidationError(
        "Use an NSE symbol such as RELIANCE or a six-digit BSE code such as 500325.BO."
    )


def parse_nse_symbol_master(csv_text: str, as_of: date) -> list[SymbolRecord]:
    """Parse an official NSE symbol master after validating its schema."""

    reader = csv.DictReader(StringIO(csv_text.lstrip("\ufeff")), skipinitialspace=True)
    fieldnames = set(reader.fieldnames or ())
    if not _NSE_COLUMNS.issubset(fieldnames):
        missing = ", ".join(sorted(_NSE_COLUMNS - fieldnames))
        raise ValueError(f"NSE symbol master is missing required columns: {missing}")

    records = [
        SymbolRecord(
            symbol=f"{row['SYMBOL'].strip().upper()}.NS",
            name=row["NAME OF COMPANY"].strip(),
            exchange="NSE",
            snapshot_date=as_of,
        )
        for row in reader
        if row.get("SERIES", "").strip().upper() == "EQ" and row.get("SYMBOL", "").strip()
    ]
    if not records:
        raise ValueError("NSE symbol master contains no EQ-series rows")
    return sorted(records, key=lambda record: record.symbol)


def search_symbols(
    query: str, rows: Sequence[SymbolRecord], limit: int = 8
) -> list[SymbolRecord]:
    """Search a catalog with deterministic exact, prefix, then name ranking."""

    needle = query.strip().upper()
    if not needle or limit <= 0:
        return []

    def rank(record: SymbolRecord) -> tuple[int, str]:
        bare_symbol = record.symbol.removesuffix(".NS")
        if needle in {bare_symbol, record.symbol}:
            priority = 0
        elif bare_symbol.startswith(needle):
            priority = 1
        elif needle in bare_symbol or needle in record.name.upper():
            priority = 2
        else:
            priority = 3
        return priority, record.symbol

    matches = [record for record in rows if rank(record)[0] < 3]
    return sorted(matches, key=rank)[: min(limit, 8)]


def serialize_symbol_catalog(rows: Sequence[SymbolRecord]) -> str:
    """Serialize a validated catalog in a stable, versionable format."""

    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("symbol", "name", "exchange", "snapshot_date"))
    for record in sorted(rows, key=lambda item: item.symbol):
        writer.writerow(
            (record.symbol, record.name, record.exchange, record.snapshot_date.isoformat())
        )
    return buffer.getvalue()
