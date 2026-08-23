"""Bounded live OpenBB smoke check with honest provider diagnostics."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from datetime import date, timedelta
from pathlib import Path
from queue import Empty
from typing import Any

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _worker(symbol: str, provider: str, output: Any) -> None:
    from nivesh.providers.openbb_gateway import OpenBBGateway

    gateway = OpenBBGateway.from_openbb(provider=provider)
    profile = gateway.fetch_profile(symbol)
    prices = gateway.fetch_prices(symbol, date.today() - timedelta(days=14))
    diagnostics = {
        "symbol": symbol,
        "provider": provider,
        "datasets": {
            "profile": {
                "available": profile.coverage > 0,
                "as_of": str(profile.as_of) if profile.as_of else None,
                "warnings": list(profile.warnings),
            },
            "prices": {
                "available": bool(prices.data),
                "observations": len(prices.data),
                "as_of": str(prices.as_of) if prices.as_of else None,
                "warnings": list(prices.warnings),
            },
        },
    }
    output.put(diagnostics)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="RELIANCE.NS")
    parser.add_argument("--provider", default="yfinance")
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    context = mp.get_context("spawn")
    output = context.Queue()
    process = context.Process(target=_worker, args=(args.symbol, args.provider, output))
    process.start()
    process.join(timeout=max(1, args.timeout))
    if process.is_alive():
        process.terminate()
        process.join(timeout=5)
        print(
            json.dumps(
                {
                    "symbol": args.symbol,
                    "provider": args.provider,
                    "status": "timeout",
                    "timeout_seconds": args.timeout,
                },
                indent=2,
            )
        )
        return 2

    try:
        diagnostics = output.get_nowait()
    except Empty:
        print(
            json.dumps(
                {
                    "symbol": args.symbol,
                    "provider": args.provider,
                    "status": "worker_failed",
                    "exit_code": process.exitcode,
                },
                indent=2,
            )
        )
        return 2

    available = any(
        dataset.get("available") for dataset in diagnostics["datasets"].values()
    )
    diagnostics["status"] = "provider_returned_data" if available else "no_dataset_available"
    print(json.dumps(diagnostics, indent=2))
    return 0 if available else 2


if __name__ == "__main__":
    raise SystemExit(main())
