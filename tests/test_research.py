from datetime import UTC, date, datetime

from nivesh.domain.models import AnalysisBundle, CompanyProfile, DatasetResult, FinancialPeriod
from nivesh.services.research import build_research_brief, research_markdown


def bundle(rows, **kwargs):
    def ds(data):
        return DatasetResult(
            data=data,
            provider="fixture",
            retrieved_at=datetime.now(UTC),
            as_of=date(2026, 3, 31),
            **kwargs,
        )

    return AnalysisBundle(
        symbol="TEST",
        profile=ds(CompanyProfile(symbol="TEST", currency="USD")),
        prices=ds([]),
        statements=ds(rows),
        metrics=ds({}),
    )


def test_loss_and_negative_equity_are_material():
    b = bundle(
        [
            FinancialPeriod(
                period_ending=date(2026, 3, 31), revenue=200, net_income=-20, total_equity=-10
            )
        ]
    )
    brief = build_research_brief(b)
    assert any("loss" in x.title.lower() for x in brief.cons)
    assert any("equity" in x.title.lower() for x in brief.cons)
    assert all(x.source == "fixture" and "2026-03-31" in x.period for x in brief.cons)


def test_missing_data_is_limitation_not_con():
    brief = build_research_brief(bundle([]))
    assert not brief.cons and not brief.pros
    assert any("statement" in x.lower() for x in brief.limitations)


def test_report_provenance_and_stale():
    b = bundle([], stale=True)
    report = research_markdown(b, build_research_brief(b))
    assert "Stale" in report and "fixture" in report and "UTC" in report


def test_strong_growth_and_zero_debt_are_supported():
    b = bundle(
        [
            FinancialPeriod(
                period_ending=date(2026, 3, 31),
                revenue=120,
                net_income=20,
                total_equity=100,
                total_debt=0,
                cash=30,
                operating_cash_flow=25,
                free_cash_flow=15,
            ),
            FinancialPeriod(period_ending=date(2025, 3, 31), revenue=100, net_income=10),
        ]
    )
    brief = build_research_brief(b)
    assert any("20.0%" in x.evidence for x in brief.pros)
    assert any("0.00x" in x.evidence for x in brief.pros)
    report = research_markdown(b, brief)
    for item in brief.pros + brief.cons + brief.changes:
        assert item.evidence in report and item.period in report


def test_financial_sector_omits_industrial_rules():
    b = bundle(
        [
            FinancialPeriod(
                period_ending=date(2026, 3, 31),
                net_income=20,
                total_debt=200,
                total_equity=10,
                free_cash_flow=-30,
            )
        ]
    )
    b = b.model_copy(
        update={
            "profile": b.profile.model_copy(
                update={"data": b.profile.data.model_copy(update={"sector": "Financial Services"})}
            )
        }
    )
    brief = build_research_brief(b)
    assert not any("leverage" in x.title or "cash flow" in x.title for x in brief.cons)
    assert any("Financial sector" in x for x in brief.limitations)


def test_quarter_is_not_extrapolated_and_demo_is_explicit():
    b = bundle([FinancialPeriod(period_ending=date(2026, 3, 31), net_income=20, free_cash_flow=10)])
    b = b.model_copy(
        update={
            "statements": b.statements.model_copy(
                update={"period": "quarterly", "provider": "demo"}
            )
        }
    )
    brief = build_research_brief(b)
    assert any("this quarter" in x.evidence for x in brief.pros)
    assert not brief.valuation_context
    assert "DEMO DATA" in research_markdown(b, brief)


def test_full_ttm_valuation_and_unknown_source_dates():
    rows = [
        FinancialPeriod(period_ending=d, net_income=5)
        for d in [date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31), date(2026, 3, 31)]
    ]
    b = bundle(rows)
    b = b.model_copy(
        update={
            "statements": b.statements.model_copy(update={"period": "quarterly"}),
            "profile": b.profile.model_copy(
                update={
                    "as_of": None,
                    "data": b.profile.data.model_copy(update={"market_cap": 1000}),
                }
            ),
        }
    )
    brief = build_research_brief(b)
    assert any("50.00x" in x.evidence and "TTM" in x.evidence for x in brief.valuation_context)
    assert any("source date unknown" in x for x in brief.limitations)


def test_currency_and_zero_are_preserved():
    from nivesh.ui.overview import _format_money

    assert _format_money(0, "USD") == "USD 0"
    assert "₹" not in _format_money(1000, "USD")
    assert _format_money(None, "USD") == "—"
