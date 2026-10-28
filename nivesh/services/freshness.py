"""Source-age checks independent of cache retrieval time."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TypeVar

from nivesh.domain.models import AnalysisBundle, DatasetResult

T = TypeVar("T")
FRESHNESS_POLICY = (
    "Source-age flags: prices over 7 days; annual statements over 550 days; "
    "quarterly statements over 150 days; dated provider metrics over 180 days; "
    "dated profiles over 365 days. "
    "Fetch time does not establish source freshness."
)


def assess_freshness(
    result: DatasetResult[T], *, max_age_days: int, today: date
) -> DatasetResult[T]:
    """Retain unknown dates and flag old or future-dated observations explicitly."""

    source = result.as_of.date() if isinstance(result.as_of, datetime) else result.as_of
    warnings = list(result.warnings)
    stale = result.stale
    if result.coverage > 0:
        if source is None:
            warnings.append("Source date unavailable; freshness cannot be established.")
        else:
            age = (today - source).days
            if age < 0:
                warnings.append("Source date is in the future; verify the provider record.")
                stale = True
            elif age > max_age_days:
                stale = True
                warnings.append(
                    f"Source is {age} days old (review threshold: {max_age_days} days)."
                )
    return result.model_copy(update={"stale": stale, "warnings": tuple(dict.fromkeys(warnings))})


def assess_bundle_freshness(bundle: AnalysisBundle, *, today: date | None = None) -> AnalysisBundle:
    """Apply documented thresholds while preserving per-dataset provider failures."""

    reference = today or datetime.now(UTC).date()
    return bundle.model_copy(
        update={
            "profile": assess_freshness(bundle.profile, max_age_days=365, today=reference),
            "prices": assess_freshness(bundle.prices, max_age_days=7, today=reference),
            "statements": assess_freshness(
                bundle.statements,
                max_age_days=150 if bundle.statements.period == "quarterly" else 550,
                today=reference,
            ),
            "metrics": assess_freshness(bundle.metrics, max_age_days=180, today=reference),
        }
    )
