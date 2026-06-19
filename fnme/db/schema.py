import os
import sqlalchemy as sql

def create_tables(db):
    with db.connect() as conn:
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
                node_id TEXT REFERENCES stations(node_id),
                last_updated TIMESTAMP NOT NULL,
                e5_price INTEGER,
                e10_price INTEGER,
                diesel_price INTEGER,
                PRIMARY KEY (node_id, last_updated)
            );
            """
        )
        conn.execute(create_fuel_prices_table)
        conn.commit()