import pytest
import sqlalchemy as sql
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def pg_engine():
    with PostgresContainer("postgres:16") as container:
        engine = sql.create_engine(container.get_connection_url())
        yield engine
        engine.dispose()
