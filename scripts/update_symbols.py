"""Refresh the versioned NSE equity search catalog from the official master file."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from nivesh.services.tickers import parse_nse_symbol_master, serialize_symbol_catalog

NSE_EQUITY_MASTER_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
DEFAULT_OUTPUT = Path("nivesh/assets/india_symbols.csv")


def refresh_catalog(output: Path = DEFAULT_OUTPUT, timeout: int = 30) -> int:
    """Download, validate, and atomically replace the committed symbol snapshot."""

    response = requests.get(
        NSE_EQUITY_MASTER_URL,
        headers={"User-Agent": "Mozilla/5.0 Nivesh/0.1"},
        timeout=timeout,
    )
    response.raise_for_status()
    snapshot_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    records = parse_nse_symbol_master(response.text, as_of=snapshot_date)
    rendered = serialize_symbol_catalog(records)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(rendered, encoding="utf-8", newline="")
    temporary.replace(output)
    return len(records)


def main() -> int:
    """Command-line entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    count = refresh_catalog(output=args.output, timeout=args.timeout)
    print(f"Wrote {count} NSE EQ-series symbols to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
