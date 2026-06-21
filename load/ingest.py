import json

import sqlalchemy as sql


def ingest_stations(engine, stations: list[dict]) -> int:
    if not stations:
        return 0

    params = [
        {
            **station,
            "location": json.dumps(station["location"]),
            "amenities": json.dumps(station["amenities"]),
            "opening_times": json.dumps(station["opening_times"]),
            "fuel_types": json.dumps(station["fuel_types"]),
        }
        for station in stations
    ]

    with engine.begin() as conn:
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
        """), params)

    return len(stations)


def ingest_prices(engine, prices: list[dict]) -> int:
    if not prices:
        return 0

    params = [
        {
            **price,
            "fuel_prices": json.dumps(price["fuel_prices"]),
        }
        for price in prices
    ]

    with engine.begin() as conn:
        conn.execute(sql.text("""
            INSERT INTO raw.fuel_prices (
                node_id, public_phone_number, trading_name, fuel_prices
            ) VALUES (
                :node_id, :public_phone_number, :trading_name,
                CAST(:fuel_prices AS jsonb)
            )
        """), params)

    return len(prices)


def start_pipeline_run(engine, is_incremental: bool) -> int:
    with engine.begin() as conn:
        result = conn.execute(sql.text("""
            INSERT INTO raw.pipeline_runs (is_incremental)
            VALUES (:is_incremental)
            RETURNING id
        """), {"is_incremental": is_incremental})
        return result.fetchone()[0]


def complete_pipeline_run(engine, run_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(sql.text("""
            UPDATE raw.pipeline_runs
            SET run_completed_at = NOW()
            WHERE id = :id
        """), {"id": run_id})


def get_last_run_timestamp(engine) -> str | None:
    with engine.connect() as conn:
        result = conn.execute(sql.text("""
            SELECT run_completed_at FROM raw.pipeline_runs
            WHERE run_completed_at IS NOT NULL
            ORDER BY run_completed_at DESC
            LIMIT 1
        """))
        row = result.fetchone()
        return row[0].isoformat() if row else None
