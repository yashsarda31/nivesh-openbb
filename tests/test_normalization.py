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


def test_provider_field_name_variants_fill_revenue_and_equity() -> None:
    """openbb-yfinance names revenue total_revenue and equity common_stock_equity."""

    periods = normalize_statements(
        income=[
            {
                "period_ending": "2025-03-31",
                "total_revenue": 1_000.0,
                "operating_income": 150.0,
                "net_income": 80.0,
            }
        ],
        balance=[
            {
                "period_ending": "2025-03-31",
                "total_assets": 2_100.0,
                "common_stock_equity": 1_000.0,
                "total_debt": 400.0,
            }
        ],
        cash=[],
    )

    assert periods[-1].revenue == 1_000.0
    assert periods[-1].total_equity == 1_000.0


def test_priority_order_prefers_canonical_keys_over_variants() -> None:
    """Map order decides which provider variant fills a destination first."""

    periods = normalize_statements(
        income=[
            {
                "period_ending": "2025-03-31",
                "revenue": 1_000.0,
                "total_revenue": 999.0,
            }
        ],
        balance=[
            {
                "period_ending": "2025-03-31",
                "total_equity": 1_000.0,
                "common_stock_equity": 800.0,
            }
        ],
        cash=[],
    )

    assert periods[-1].revenue == 1_000.0
    assert periods[-1].total_equity == 1_000.0


def test_null_variant_does_not_block_fallback_value() -> None:
    """A present-but-null variant must not shadow a later populated variant."""

    periods = normalize_statements(
        income=[{"period_ending": "2025-03-31", "revenue": None, "total_revenue": 750.0}],
        balance=[
            {
                "period_ending": "2025-03-31",
                "total_equity": None,
                "total_common_equity": 500.0,
            }
        ],
        cash=[],
    )

    assert periods[-1].revenue == 750.0
    assert periods[-1].total_equity == 500.0


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
