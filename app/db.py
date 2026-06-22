import math

import sqlalchemy as sql

_MAIN_FUELS = ("E10", "E5", "B7_STANDARD", "B7_PREMIUM")


def get_all_fuel_averages(engine) -> dict[str, dict]:
    """Latest average price and station count for each main fuel type."""
    with engine.connect() as conn:
        result = conn.execute(sql.text("""
            SELECT fuel_type,
                   ROUND(AVG(price_pence)::numeric, 1) AS avg_pence,
                   COUNT(*) AS stations
            FROM (
                SELECT DISTINCT ON (node_id, fuel_type)
                    node_id, fuel_type, price_pence
                FROM marts.fct_fuel_prices
                WHERE fuel_type = ANY(:fuels)
                  AND price_pence BETWEEN 50 AND 400
                ORDER BY node_id, fuel_type, loaded_at DESC
            ) latest
            GROUP BY fuel_type
        """), {"fuels": list(_MAIN_FUELS)})
        rows = [row._asdict() for row in result]
        return {row["fuel_type"]: row for row in rows}


def get_region_rankings(
    engine, fuel_type: str = "E10", top_n: int = 5, min_stations: int = 10
) -> dict[str, list[dict]]:
    """Cheapest and most expensive counties for a given fuel type."""
    rows = get_all_regions(engine, fuel_type=fuel_type, min_stations=min_stations)
    return {"cheapest": rows[:top_n], "dearest": rows[-top_n:][::-1]}


def get_all_regions(
    engine, fuel_type: str = "E10", min_stations: int = 10
) -> list[dict]:
    """All counties sorted cheapest first, for the regions table."""
    with engine.connect() as conn:
        result = conn.execute(sql.text("""
            SELECT county,
                   ROUND(AVG(price_pence)::numeric, 1) AS avg_pence,
                   COUNT(*) AS stations
            FROM (
                SELECT DISTINCT ON (node_id)
                    node_id, county, price_pence
                FROM marts.fct_fuel_prices
                WHERE fuel_type = :fuel_type
                  AND price_pence BETWEEN 50 AND 400
                  AND county IS NOT NULL
                  AND county <> ''
                ORDER BY node_id, loaded_at DESC
            ) latest
            GROUP BY county
            HAVING COUNT(*) >= :min_stations
            ORDER BY avg_pence
        """), {"fuel_type": fuel_type, "min_stations": min_stations})
        return [row._asdict() for row in result]


def get_last_updated(engine) -> str | None:
    """ISO timestamp of the most recent pipeline snapshot, or None."""
    with engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT MAX(loaded_at) FROM marts.fct_fuel_prices"
        ))
        val = result.scalar()
        return val.isoformat() if val else None


def get_latest_prices(engine, fuel_type: str = "E10") -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(sql.text("""
            SELECT DISTINCT ON (node_id)
                node_id, trading_name, brand_name, fuel_type, price_pence,
                latitude, longitude, postcode, city
            FROM marts.fct_fuel_prices
            WHERE fuel_type = :fuel_type
              AND price_pence BETWEEN 50 AND 400
            ORDER BY node_id, loaded_at DESC
        """), {"fuel_type": fuel_type})
        return [row._asdict() for row in result]


def get_fuel_deltas(engine) -> dict[str, float | None]:
    """Day-over-day price change (pence) for each main fuel type.

    Returns a dict keyed by fuel_type; value is today_avg - yesterday_avg,
    or None when fewer than two days of data exist for that fuel.
    """
    with engine.connect() as conn:
        result = conn.execute(sql.text("""
            WITH daily AS (
                SELECT fuel_type,
                       loaded_at::date AS day,
                       AVG(price_pence) AS avg_pence
                FROM marts.fct_fuel_prices
                WHERE fuel_type = ANY(:fuels)
                  AND price_pence BETWEEN 50 AND 400
                GROUP BY fuel_type, loaded_at::date
            ),
            ranked AS (
                SELECT fuel_type, day, avg_pence,
                       ROW_NUMBER() OVER (
                           PARTITION BY fuel_type ORDER BY day DESC
                       ) AS rn
                FROM daily
            )
            SELECT
                t.fuel_type,
                t.avg_pence - y.avg_pence AS delta
            FROM ranked t
            JOIN ranked y
              ON t.fuel_type = y.fuel_type
             AND t.rn = 1 AND y.rn = 2
        """), {"fuels": list(_MAIN_FUELS)})
        rows = [row._asdict() for row in result]
        return {r["fuel_type"]: float(r["delta"]) for r in rows}


def get_price_trend(engine, fuel_type: str = "E10") -> list[dict]:
    """Daily national average price, oldest first. Empty when < 2 days exist."""
    with engine.connect() as conn:
        result = conn.execute(sql.text("""
            SELECT loaded_at::date AS day,
                   ROUND(AVG(price_pence)::numeric, 1) AS avg_pence
            FROM marts.fct_fuel_prices
            WHERE fuel_type = :fuel_type
              AND price_pence BETWEEN 50 AND 400
            GROUP BY loaded_at::date
            ORDER BY day
        """), {"fuel_type": fuel_type})
        return [row._asdict() for row in result]


def get_best_days(engine, fuel_type: str = "E10") -> dict:
    """Day-of-week average prices and count of distinct days of data available."""
    with engine.connect() as conn:
        distinct_days = conn.execute(sql.text("""
            SELECT COUNT(DISTINCT loaded_at::date)
            FROM marts.fct_fuel_prices
            WHERE fuel_type = :fuel_type
              AND price_pence BETWEEN 50 AND 400
        """), {"fuel_type": fuel_type}).scalar() or 0

        result = conn.execute(sql.text("""
            SELECT EXTRACT(DOW FROM loaded_at)::int AS dow,
                   TRIM(TO_CHAR(loaded_at, 'Day'))  AS day_name,
                   ROUND(AVG(price_pence)::numeric, 1) AS avg_pence
            FROM marts.fct_fuel_prices
            WHERE fuel_type = :fuel_type
              AND price_pence BETWEEN 50 AND 400
            GROUP BY dow, day_name
            ORDER BY dow
        """), {"fuel_type": fuel_type})
        rows = [row._asdict() for row in result]
        return {"rows": rows, "days_available": int(distinct_days)}


def get_nearby_stations(
    engine, lat: float, lon: float, radius_miles: float = 5.0
) -> list[dict]:
    deg_lat = radius_miles / 69.0
    deg_lon = radius_miles / (69.0 * math.cos(math.radians(lat)))

    with engine.connect() as conn:
        result = conn.execute(sql.text("""
            SELECT DISTINCT ON (node_id, fuel_type)
                node_id, trading_name, fuel_type, price_pence,
                latitude, longitude, postcode, city,
                is_motorway_service_station, is_supermarket_service_station
            FROM marts.fct_fuel_prices
            WHERE latitude  BETWEEN :min_lat AND :max_lat
              AND longitude BETWEEN :min_lon AND :max_lon
              AND price_pence BETWEEN 50 AND 400
            ORDER BY node_id, fuel_type, loaded_at DESC
        """), {
            "min_lat": lat - deg_lat, "max_lat": lat + deg_lat,
            "min_lon": lon - deg_lon, "max_lon": lon + deg_lon,
        })
        rows = [row._asdict() for row in result]

    return [
        r
        for r in rows
        if _haversine(lat, lon, r["latitude"], r["longitude"]) <= radius_miles
    ]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
