"""Null-safe financial ratio helpers."""

from __future__ import annotations

from math import isfinite


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Divide finite inputs, preserving missing and invalid denominator states."""

    if numerator is None or denominator is None or denominator == 0:
        return None
    result = numerator / denominator
    return result if isfinite(result) else None


def average_balance(current: float | None, previous: float | None) -> float | None:
    """Return an average balance, falling back to the available period."""

    if current is None:
        return previous
    if previous is None:
        return current
    return (current + previous) / 2.0


def cagr(start: float | None, end: float | None, years: float) -> float | None:
    """Calculate CAGR only when its economic inputs are meaningful."""

    if start is None or end is None or start <= 0 or end < 0 or years <= 0:
        return None
    result = (end / start) ** (1.0 / years) - 1.0
    return result if isfinite(result) else None
