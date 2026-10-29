"""Contracts for the escaped HTML chrome and card-width number formats."""

from nivesh.ui import kit
from nivesh.ui.overview import format_compact_money
from nivesh.ui.workspace import symbol_catalog

HOSTILE = '<img src=x onerror="alert(1)">'


def test_provider_text_is_escaped_in_every_html_block() -> None:
    blocks = [
        kit.topbar([HOSTILE], [(HOSTILE, "info")], code=HOSTILE),
        kit.chips([HOSTILE, HOSTILE]),
        kit.status_list([(HOSTILE, "ok", HOSTILE, HOSTILE)]),
        kit.key_values([(HOSTILE, HOSTILE)]),
        kit.stat_strip([(HOSTILE, HOSTILE, "up")]),
        kit.component_bars([(HOSTILE, 50, 0.5, HOSTILE)]),
        kit.quote_block(currency="INR", close=1.0, change=0.01, caption=HOSTILE),
        kit.footer(HOSTILE, HOSTILE),
        kit.monogram("<b>.NS"),
    ]
    for block in blocks:
        assert "<img src=x" not in block
        assert "onerror=\"alert" not in block


def test_quote_and_ring_never_invent_missing_values() -> None:
    quote = kit.quote_block(currency="INR", close=None, change=None, caption="Last close")
    assert "—" in quote and "Change unavailable" in quote
    ring = kit.score_ring(None)
    assert "withheld" in ring and "--nv-p:0" in ring
    assert "63 out of 100" in kit.score_ring(63)


def test_icons_are_inert_data_images() -> None:
    mark = kit.brand_mark()
    assert mark.startswith("<img") and "data:image/svg+xml;base64," in mark
    assert "<svg" not in mark


def test_compact_money_switches_to_lakh_crore_only_for_large_inr() -> None:
    assert format_compact_money(10_572_190_000_000, "INR") == "₹ 10.57 L Cr"
    assert format_compact_money(535_700_000_000, "INR") == "₹ 53,570 Cr"
    assert format_compact_money(2_000_000_000_000, "USD") == "USD 2,000,000,000,000"
    assert format_compact_money(None, "INR") == "—"


def test_symbol_catalog_is_versioned_nse_listings() -> None:
    catalog = dict(symbol_catalog())
    assert len(catalog) > 2000
    assert catalog["RELIANCE.NS"].startswith("Reliance Industries")
    assert all(symbol.endswith(".NS") for symbol in catalog)
