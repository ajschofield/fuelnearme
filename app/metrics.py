"""Pure aggregation helpers over the price rows returned by app.db.

These take the plain list[dict] that get_latest_prices produces (one row per
station for a single fuel type) and derive the figures shown in the UI. Kept
free of Streamlit and the database so they can be unit-tested in isolation.
"""

from __future__ import annotations

from statistics import mean


def pretty_name(name: str | None) -> str:
    """Humanise a SHOUTING raw station/brand string.

    Title-cases each word but leaves short all-caps tokens (BP, MFG, HVO, JET)
    intact, since those are acronyms rather than shouting.
    """
    if not name:
        return ""
    words = []
    for word in name.split():
        if word.isupper() and word.isalpha() and len(word) <= 3:
            words.append(word)
        else:
            words.append(word.capitalize())
    return " ".join(words)


def summary_stats(prices: list[dict]) -> dict | None:
    """Headline figures for the selected fuel: average, cheapest, spread.

    Returns None when there are no prices so callers can show an empty state.
    """
    if not prices:
        return None

    values = [float(p["price_pence"]) for p in prices]
    cheapest = min(prices, key=lambda p: float(p["price_pence"]))
    dearest = max(prices, key=lambda p: float(p["price_pence"]))

    return {
        "count": len(values),
        "mean_pence": mean(values),
        "min_pence": min(values),
        "max_pence": max(values),
        "spread_pence": max(values) - min(values),
        "cheapest": cheapest,
        "dearest": dearest,
    }


def brand_averages(
    prices: list[dict], top_n: int = 8, min_stations: int = 10
) -> list[dict]:
    """Average price per brand, cheapest first.

    Brands with no name or fewer than `min_stations` samples are dropped so a
    single outlier forecourt cannot top the table.
    """
    groups: dict[str, list[float]] = {}
    for p in prices:
        brand = p.get("brand_name")
        if not brand:
            continue
        brand = pretty_name(brand.strip())
        groups.setdefault(brand, []).append(float(p["price_pence"]))

    rows = [
        {"brand": brand, "avg_pence": mean(vals), "stations": len(vals)}
        for brand, vals in groups.items()
        if len(vals) >= min_stations
    ]
    rows.sort(key=lambda r: r["avg_pence"])
    return rows[:top_n]
