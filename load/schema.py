import sqlalchemy as sql


def create_raw_schema(engine) -> None:
    with engine.begin() as conn:
        conn.execute(sql.text("CREATE SCHEMA IF NOT EXISTS raw"))

        conn.execute(sql.text("""
            CREATE TABLE IF NOT EXISTS raw.stations (
                node_id                        TEXT PRIMARY KEY,
                public_phone_number            TEXT,
                trading_name                   TEXT NOT NULL,
                is_same_trading_and_brand_name BOOLEAN,
                brand_name                     TEXT,
                temporary_closure              BOOLEAN,
                permanent_closure              BOOLEAN,
                permanent_closure_date         DATE,
                is_motorway_service_station    BOOLEAN,
                is_supermarket_service_station BOOLEAN,
                location                       JSONB NOT NULL,
                amenities                      JSONB,
                opening_times                  JSONB,
                fuel_types                     JSONB,
                loaded_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        conn.execute(sql.text("""
            CREATE TABLE IF NOT EXISTS raw.fuel_prices (
                node_id             TEXT NOT NULL,
                public_phone_number TEXT,
                trading_name        TEXT,
                fuel_prices         JSONB NOT NULL,
                loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        conn.execute(sql.text("""
            CREATE TABLE IF NOT EXISTS raw.pipeline_runs (
                id               SERIAL PRIMARY KEY,
                run_started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                run_completed_at TIMESTAMPTZ,
                is_incremental   BOOLEAN NOT NULL DEFAULT FALSE
            )
        """))

