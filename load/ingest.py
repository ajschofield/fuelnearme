import json

import sqlalchemy as sql


def ingest_stations(engine, stations: list[dict]) -> int:
    if not stations:
        return 0

    with engine.connect() as conn:
        for station in stations:
            conn.execute(sql.text("""
                INSERT INTO raw.stations (
                    node_id, public_phone_number, trading_name,
                    is_same_trading_and_brand_name, brand_name,
                    temporary_closure, permanent_closure, permanent_closure_date,
                    is_motorway_service_station, is_supermarket_service_station,
                    location, amenities, opening_times, fuel_types
                ) VALUES (
                    :node_id, :public_phone_number, :trading_name,
                    :is_same_trading_and_brand_name, :brand_name,
                    :temporary_closure, :permanent_closure, :permanent_closure_date,
                    :is_motorway_service_station, :is_supermarket_service_station,
                    CAST(:location AS jsonb), CAST(:amenities AS jsonb),
                    CAST(:opening_times AS jsonb), CAST(:fuel_types AS jsonb)
                )
                ON CONFLICT (node_id) DO UPDATE SET
                    public_phone_number            = EXCLUDED.public_phone_number,
                    trading_name                   = EXCLUDED.trading_name,
                    is_same_trading_and_brand_name = EXCLUDED.is_same_trading_and_brand_name,
                    brand_name                     = EXCLUDED.brand_name,
                    temporary_closure              = EXCLUDED.temporary_closure,
                    permanent_closure              = EXCLUDED.permanent_closure,
                    permanent_closure_date         = EXCLUDED.permanent_closure_date,
                    is_motorway_service_station    = EXCLUDED.is_motorway_service_station,
                    is_supermarket_service_station = EXCLUDED.is_supermarket_service_station,
                    location                       = EXCLUDED.location,
                    amenities                      = EXCLUDED.amenities,
                    opening_times                  = EXCLUDED.opening_times,
                    fuel_types                     = EXCLUDED.fuel_types,
                    loaded_at                      = NOW()
            """), {
                **station,
                "location": json.dumps(station["location"]),
                "amenities": json.dumps(station["amenities"]),
                "opening_times": json.dumps(station["opening_times"]),
                "fuel_types": json.dumps(station["fuel_types"]),
            })
        conn.commit()

    return len(stations)


def ingest_prices(engine, prices: list[dict]) -> int:
    if not prices:
        return 0

    with engine.connect() as conn:
        for price in prices:
            conn.execute(sql.text("""
                INSERT INTO raw.fuel_prices (
                    node_id, public_phone_number, trading_name, fuel_prices
                ) VALUES (
                    :node_id, :public_phone_number, :trading_name,
                    CAST(:fuel_prices AS jsonb)
                )
            """), {
                **price,
                "fuel_prices": json.dumps(price["fuel_prices"]),
            })
        conn.commit()

    return len(prices)
