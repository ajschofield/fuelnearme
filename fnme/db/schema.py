import os
import sqlalchemy as sql

DATABASE_URL = os.environ["DATABASE_URL"]

engine = sql.create_engine(DATABASE_URL, echo=False)

def create_tables():
    with engine.connect() as conn:
        create_stations_table = sql.text(
            """
            CREATE TABLE IF NOT EXISTS stations (
                node_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                latitude FLOAT NOT NULL,
                longitude FLOAT NOT NULL
            );
            """
        )
        conn.execute(create_stations_table)
        create_fuel_prices_table = sql.text(
            """
            CREATE TABLE IF NOT EXISTS fuel_prices (
                node_id TEXT REFERENCES stations(node_id) PRIMARY KEY,
                e5_price INTEGER,
                e10_price INTEGER,
                diesel_price INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(create_fuel_prices_table)
        conn.commit()