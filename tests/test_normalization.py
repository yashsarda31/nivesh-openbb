from datetime import date

from nivesh.services.normalization import enrich_periods, normalize_statements


def test_aligns_statements_by_period_ending() -> None:
    periods = normalize_statements(
        income=[
            {"period_ending": "2024-03-31", "revenue": 800.0, "net_income": 60.0},
            {
                "period_ending": "2025-03-31",
                "fiscal_year": 2025,
                "reported_currency": "INR",
                "revenue": 1_000.0,
                "operating_income": 150.0,
                "net_income": 80.0,
            },
        ],
        balance=[
            {"period_ending": "2024-03-31", "total_equity": 900.0},
            {
                "period_ending": "2025-03-31",
                "total_assets": 2_100.0,
                "total_equity": 1_000.0,
                "total_debt": 0.0,
                "total_current_assets": 600.0,
                "total_current_liabilities": 300.0,
            },
        ],
        cash=[
            {
                "period_ending": "2025-03-31",
                "operating_cash_flow": 120.0,
                "capital_expenditure": -50.0,
            }
        ],
    )

    assert [row.period_ending for row in periods] == [date(2024, 3, 31), date(2025, 3, 31)]
    assert periods[-1].revenue == 1_000.0
    assert periods[-1].total_debt == 0.0
    assert periods[-1].currency == "INR"


def test_enriches_periods_with_average_balance_ratios() -> None:
    periods = normalize_statements(
        income=[
            {"period_ending": "2024-03-31", "net_income": 60.0},
            {
                "period_ending": "2025-03-31",
                "revenue": 1_000.0,
                "operating_income": 150.0,
                "net_income": 80.0,
            },
        ],
        balance=[
            {"period_ending": "2024-03-31", "total_assets": 2_000.0, "total_equity": 900.0},
            {
                "period_ending": "2025-03-31",
                "total_assets": 2_100.0,
                "total_equity": 1_000.0,
                "total_debt": 400.0,
            },
        ],
        cash=[
            {
                "period_ending": "2025-03-31",
                "operating_cash_flow": 120.0,
                "capital_expenditure": -50.0,
            }
        ],
    )

    enriched = enrich_periods(periods)
    latest = enriched[-1]

    assert latest.metrics["operating_margin"] == 0.15
    assert latest.metrics["roe"] == 80.0 / 950.0
    assert latest.metrics["roa"] == 80.0 / 2_050.0
    assert latest.metrics["cash_conversion"] == 1.5
    assert latest.free_cash_flow == 70.0
