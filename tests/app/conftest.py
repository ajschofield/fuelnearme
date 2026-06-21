import pytest
import sqlalchemy as sql
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def app_engine():
    with PostgresContainer("postgres:16") as container:
        engine = sql.create_engine(container.get_connection_url())
        with engine.connect() as conn:
            conn.execute(sql.text("CREATE SCHEMA IF NOT EXISTS marts"))
            conn.execute(sql.text("""
                CREATE TABLE marts.fct_fuel_prices (
                    node_id          TEXT,
                    trading_name     TEXT,
                    brand_name       TEXT,
                    fuel_type        TEXT,
                    price_pence      NUMERIC,
                    price_last_updated TIMESTAMPTZ,
                    price_change_effective_timestamp TIMESTAMPTZ,
                    loaded_at        TIMESTAMPTZ,
                    is_motorway_service_station    BOOLEAN,
                    is_supermarket_service_station BOOLEAN,
                    city             TEXT,
                    county           TEXT,
                    country          TEXT,
                    postcode         TEXT,
                    latitude         FLOAT,
                    longitude        FLOAT
                )
            """))
            conn.execute(sql.text("""
                CREATE TABLE marts.dim_stations (
                    node_id                        TEXT PRIMARY KEY,
                    trading_name                   TEXT,
                    brand_name                     TEXT,
                    is_motorway_service_station    BOOLEAN,
                    is_supermarket_service_station BOOLEAN,
                    temporary_closure              BOOLEAN,
                    permanent_closure              BOOLEAN,
                    address_line_1                 TEXT,
                    city                           TEXT,
                    county                         TEXT,
                    country                        TEXT,
                    postcode                       TEXT,
                    latitude                       FLOAT,
                    longitude                      FLOAT,
                    amenities                      JSONB,
                    fuel_types                     JSONB
                )
            """))
            conn.commit()
        yield engine
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_app_tables(app_engine):
    yield
    with app_engine.connect() as conn:
        conn.execute(sql.text("TRUNCATE marts.fct_fuel_prices, marts.dim_stations"))
        conn.commit()
