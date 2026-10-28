"""Transparent statement-backed research observations."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nivesh.domain.models import AnalysisBundle, DatasetResult
from nivesh.services.freshness import FRESHNESS_POLICY
from nivesh.services.fundamentals import ALIASES, fundamental_inputs
from nivesh.services.normalization import comparable_period, enrich_periods

METHODOLOGY = (
    "Generic rules, not peer comparisons: positive profit, FCF and growth support observations; "
    "Losses, contraction, negative equity, debt/equity above 1 and current ratio below 1 "
    "flag risks. "
    "Cash conversion requires positive income. No moat, management or cheap/expensive inference. "
    "Research support, not buy/sell advice."
)
CHECKS = (
    "Research checklist: verify exchange filings, audit notes, segment trends, related-party "
    "transactions, ownership/pledges and sector peers. "
    "Suggested checks are not identified weaknesses."
)


@dataclass(frozen=True)
class ResearchObservation:
    title: str
    evidence: str
    source: str
    period: str


@dataclass
class ResearchBrief:
    pros: list[ResearchObservation] = field(default_factory=list)
    cons: list[ResearchObservation] = field(default_factory=list)
    changes: list[ResearchObservation] = field(default_factory=list)
    valuation_context: list[ResearchObservation] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _datasets(bundle: AnalysisBundle) -> list[tuple[str, DatasetResult[Any]]]:
    return [
        ("Profile", bundle.profile),
        ("Prices", bundle.prices),
        ("Statements", bundle.statements),
        ("Metrics", bundle.metrics),
    ]


def build_research_brief(bundle: AnalysisBundle) -> ResearchBrief:
    brief = ResearchBrief()
    ds = bundle.statements
    frequency = ds.period or "annual"
    quarterly = frequency in {"quarter", "quarterly"}
    rows = enrich_periods(ds.data, frequency)
    inputs = fundamental_inputs(
        rows, bundle.metrics.data, frequency, bundle.profile.data.market_cap
    )
    currency = ds.currency or bundle.profile.data.currency or "currency unknown"
    financial = any(
        word
        in ((bundle.profile.data.sector or "") + " " + (bundle.profile.data.industry or "")).lower()
        for word in ("financial", "bank", "insurance", "credit services", "capital markets")
    )
    for name, result in _datasets(bundle):
        if result.stale:
            brief.limitations.append(
                f"Stale {name.lower()} data: verify newer source records before use."
            )
        if result.as_of is None:
            brief.limitations.append(
                f"{name}: source date unknown; retrieval date does not establish freshness."
            )
        if result.coverage < 1:
            brief.limitations.append(
                f"{name}: coverage {result.coverage:.0%}; missing values remain unknown."
            )
        brief.limitations.extend(f"{name}: {warning}" for warning in result.warnings)
        if "demo" in result.provider.lower():
            brief.limitations.append("DEMO DATA: illustrative fixture; not live company evidence.")
    brief.limitations.append(
        "Consolidated/standalone scope is not supplied by the current provider; "
        "verify exchange filings."
    )
    brief.limitations.append(FRESHNESS_POLICY)
    if ds.period is None:
        brief.limitations.append(
            "Reporting frequency unspecified; annual rules assumed. Verify filing frequency."
        )
    if financial:
        brief.limitations.append(
            "Financial sector: industrial leverage, liquidity, operating margin "
            "and cash conversion rules omitted."
        )
    if not rows:
        brief.limitations.append(
            "No statements available; no statement-backed pros or cons can be established."
        )
        return brief
    latest = rows[-1]
    period = f"{frequency} ending {latest.period_ending.isoformat()}"
    previous = comparable_period(rows, latest)

    def observe(title: str, evidence: str, positive: bool) -> None:
        (brief.pros if positive else brief.cons).append(
            ResearchObservation(title, evidence, ds.provider, period)
        )

    def money(value: float) -> str:
        return f"{currency} {value:,.2f}"

    if latest.net_income is not None:
        observe(
            "Profitable period"
            if latest.net_income > 0
            else "Net loss"
            if latest.net_income < 0
            else "Break-even income",
            f"Net income {money(latest.net_income)}.",
            latest.net_income > 0,
        )
    if latest.total_equity is not None and latest.total_equity <= 0:
        observe(
            "Nonpositive equity",
            f"Total equity {money(latest.total_equity)}; equity-based returns are not meaningful.",
            False,
        )
    for label, attr in [("Revenue", "revenue"), ("Net income", "net_income")]:
        current = getattr(latest, attr)
        prior = getattr(previous, attr) if previous else None
        if current is not None and prior is not None and previous:
            evidence = (
                f"{money(prior)} ({previous.period_ending}) to "
                f"{money(current)} ({latest.period_ending})."
            )
            if prior > 0:
                growth = current / prior - 1
                evidence += f" YoY change {growth:+.1%}."
                if growth != 0:
                    observe(
                        f"{label} grew" if growth > 0 else f"{label} contracted",
                        evidence,
                        growth > 0,
                    )
            brief.changes.append(
                ResearchObservation(f"{label} change", evidence, ds.provider, period)
            )
    if not previous:
        brief.limitations.append(
            "Same-date prior-year statement unavailable; YoY changes cannot be established."
        )
    if not financial:
        if latest.operating_income is not None and latest.operating_income < 0:
            observe("Operating loss", f"Operating income {money(latest.operating_income)}.", False)
        if (
            latest.revenue is not None
            and latest.revenue > 0
            and previous
            and previous.revenue
            and previous.revenue > 0
            and latest.operating_income is not None
            and previous.operating_income is not None
        ):
            margin = latest.operating_income / latest.revenue
            old_margin = previous.operating_income / previous.revenue
            delta = (margin - old_margin) * 100
            evidence = (
                f"Operating margin {old_margin:.1%} ({previous.period_ending}) "
                f"to {margin:.1%}; {delta:+.1f} percentage points."
            )
            brief.changes.append(
                ResearchObservation("Operating margin change", evidence, ds.provider, period)
            )
            if abs(delta) >= 1:
                observe(
                    "Margin expanded" if delta > 0 else "Margin compressed", evidence, delta > 0
                )
        if latest.free_cash_flow is not None:
            basis = "quarter" if quarterly else "annual period"
            observe(
                "Positive free cash flow"
                if latest.free_cash_flow > 0
                else "Nonpositive free cash flow",
                f"Free cash flow {money(latest.free_cash_flow)} for this {basis}.",
                latest.free_cash_flow > 0,
            )
        conversion = latest.metrics.get("cash_conversion")
        if (
            conversion is not None
            and latest.net_income is not None
            and latest.net_income > 0
            and latest.operating_cash_flow is not None
        ):
            observe(
                "Cash covers earnings" if conversion >= 1 else "Cash below earnings",
                f"Operating cash flow {money(latest.operating_cash_flow)} / "
                f"net income {money(latest.net_income)} = {conversion:.2f}x.",
                conversion >= 1,
            )
        de = latest.metrics.get("debt_equity")
        if (
            de is not None
            and latest.total_equity is not None
            and latest.total_equity > 0
            and latest.total_debt is not None
            and de >= 0
            and (de <= 0.5 or de > 1)
        ):
            observe(
                "Low balance-sheet leverage" if de <= 0.5 else "Elevated balance-sheet leverage",
                f"Debt {money(latest.total_debt)} / "
                f"equity {money(latest.total_equity)} = {de:.2f}x.",
                de <= 0.5,
            )
        if (
            latest.cash is not None
            and latest.total_debt is not None
            and latest.cash > latest.total_debt
        ):
            observe(
                "Net cash position",
                f"Cash {money(latest.cash)} less debt {money(latest.total_debt)} "
                f"= {money(latest.cash - latest.total_debt)}.",
                True,
            )
        ca, cl = latest.total_current_assets, latest.total_current_liabilities
        if ca is not None and cl is not None and cl > 0 and ca / cl < 1:
            observe(
                "Current liabilities exceed current assets",
                f"Current assets {money(ca)} / current liabilities {money(cl)} = {ca / cl:.2f}x.",
                False,
            )
    growth3 = latest.metrics.get("revenue_cagr_3y")
    if growth3 is not None and not quarterly:
        observe(
            "Three-year revenue growth" if growth3 > 0 else "Three-year revenue contraction",
            f"Revenue CAGR {growth3:.1%} across three reporting years "
            f"ending {latest.period_ending}.",
            growth3 > 0,
        )
    pe = inputs.get("pe_ratio")
    if pe is not None:
        provider_pe = next(
            (
                bundle.metrics.data[key]
                for key in ALIASES["pe_ratio"]
                if bundle.metrics.data.get(key) is not None
            ),
            None,
        )
        source = (
            bundle.metrics.provider
            if provider_pe is not None
            else f"{ds.provider}; market cap: {bundle.profile.provider}"
        )
        basis = (
            f"provider metric, source date {bundle.metrics.as_of or 'unknown'}"
            if provider_pe is not None
            else (
                f"{'TTM' if quarterly else 'annual'} statement income; "
                f"market-cap source date {bundle.profile.as_of or 'unknown'}"
            )
        )
        brief.valuation_context.append(
            ResearchObservation(
                "P/E context",
                f"{pe:.2f}x; {basis}. No peer-relative valuation conclusion.",
                source,
                period,
            )
        )
    missing = [
        name
        for name in ("revenue", "net_income", "operating_cash_flow", "total_equity")
        if getattr(latest, name) is None
    ]
    if missing:
        brief.limitations.append("Latest statement fields unavailable: " + ", ".join(missing) + ".")
    return brief


def research_markdown(bundle: AnalysisBundle, brief: ResearchBrief) -> str:
    lines = [
        f"# {bundle.symbol} research brief",
        f"Generated UTC: {datetime.now(UTC).isoformat()}",
        "Research support, not buy/sell advice.",
    ]
    for label, ds in _datasets(bundle):
        retrieved = ds.retrieved_at
        if retrieved.tzinfo is None:
            retrieved = retrieved.replace(tzinfo=UTC)
        lines.append(
            f"{label}: provider {ds.provider}; source {ds.as_of or 'unknown'}; "
            f"retrieved UTC {retrieved.astimezone(UTC).isoformat()}; "
            f"frequency {ds.period or 'unspecified'}; coverage {ds.coverage:.0%}."
        )
    for title, items in [
        ("Pros", brief.pros),
        ("Cons", brief.cons),
        ("Recent financial changes", brief.changes),
        ("Neutral valuation context", brief.valuation_context),
    ]:
        lines += ["", f"## {title}"]
        lines.extend(
            f"- **{item.title}**: {item.evidence} Source: {item.source}; {item.period}."
            for item in items
        )
        if not items:
            lines.append("No evidence-backed observations available.")
    lines += [
        "",
        "## Data limitations",
        *["- " + item for item in brief.limitations],
        "",
        CHECKS,
        "",
        "## Rule methodology",
        METHODOLOGY,
    ]
    return "\n".join(lines)
