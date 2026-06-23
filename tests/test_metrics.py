from decimal import Decimal

from app.metrics import brand_averages, pretty_name, summary_stats


def _price(node_id, price_pence, brand=None):
    return {
        "node_id": node_id,
        "trading_name": f"Station {node_id}",
        "brand_name": brand,
        "price_pence": price_pence,
        "city": "Leeds",
    }


def test_summary_stats_returns_none_when_empty():
    assert summary_stats([]) is None


def test_summary_stats_computes_headline_figures():
    prices = [_price("a", 130.0), _price("b", 140.0), _price("c", 150.0)]
    stats = summary_stats(prices)
    assert stats["count"] == 3
    assert stats["mean_pence"] == 140.0
    assert stats["min_pence"] == 130.0
    assert stats["max_pence"] == 150.0
    assert stats["spread_pence"] == 20.0


def test_summary_stats_identifies_cheapest_and_dearest():
    prices = [_price("a", 145.0), _price("b", 129.9), _price("c", 151.0)]
    stats = summary_stats(prices)
    assert stats["cheapest"]["node_id"] == "b"
    assert stats["dearest"]["node_id"] == "c"


def test_summary_stats_handles_decimal_prices():
    # price_pence arrives from PostgreSQL NUMERIC as Decimal.
    prices = [_price("a", Decimal("130.5")), _price("b", Decimal("131.5"))]
    stats = summary_stats(prices)
    assert stats["mean_pence"] == 131.0


def test_pretty_name_humanises_shouting_names():
    assert pretty_name("MFG MORRISONS BRADFORD") == "MFG Morrisons Bradford"
    assert pretty_name("shell") == "Shell"
    assert pretty_name("BP") == "BP"
    assert pretty_name("Circle K") == "Circle K"
    assert pretty_name(None) == ""
    assert pretty_name("RONTEC OTLEY ROAD") == "Rontec Otley Road"


def test_brand_averages_merges_case_variants():
    prices = [
        _price("a", 146.0, brand="CIRCLE K"),
        _price("b", 148.0, brand="Circle K"),
        _price("c", 147.0, brand="circle k"),
    ]
    rows = brand_averages(prices, min_stations=3)
    assert len(rows) == 1
    assert rows[0]["brand"] == "Circle K"
    assert rows[0]["stations"] == 3


def test_brand_averages_groups_and_sorts_cheapest_first():
    prices = [
        _price("a", 130.0, brand="Asda"),
        _price("b", 134.0, brand="Asda"),
        _price("c", 150.0, brand="Shell"),
        _price("d", 152.0, brand="Shell"),
    ]
    rows = brand_averages(prices, min_stations=2)
    assert [r["brand"] for r in rows] == ["Asda", "Shell"]
    assert rows[0]["avg_pence"] == 132.0
    assert rows[0]["stations"] == 2


def test_brand_averages_ignores_missing_brand():
    prices = [_price("a", 130.0, brand=None), _price("b", 131.0, brand="")]
    assert brand_averages(prices, min_stations=1) == []


def test_brand_averages_respects_min_stations():
    prices = [_price("a", 130.0, brand="Solo"), _price("b", 140.0, brand="Big")]
    prices += [_price(f"x{i}", 140.0, brand="Big") for i in range(5)]
    rows = brand_averages(prices, min_stations=3)
    assert [r["brand"] for r in rows] == ["Big"]


def test_brand_averages_limits_to_top_n():
    prices = []
    for i in range(5):
        prices += [_price(f"{i}-{j}", 130 + i, brand=f"Brand{i}") for j in range(3)]
    rows = brand_averages(prices, top_n=2, min_stations=3)
    assert len(rows) == 2
    assert [r["brand"] for r in rows] == ["Brand0", "Brand1"]
