import pytest
import sqlalchemy as sql
from testcontainers.postgres import PostgresContainer

from load.schema import create_raw_schema


@pytest.fixture(scope="session")
def pg_engine():
    with PostgresContainer("postgres:16") as container:
        engine = sql.create_engine(container.get_connection_url())
        create_raw_schema(engine)
        yield engine
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_raw_tables(pg_engine):
    yield
    with pg_engine.connect() as conn:
        conn.execute(sql.text(
            "TRUNCATE raw.stations, raw.fuel_prices, raw.pipeline_runs RESTART IDENTITY"
        ))
        conn.commit()
