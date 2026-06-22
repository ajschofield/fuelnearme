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
