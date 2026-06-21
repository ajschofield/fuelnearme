import sqlalchemy as sql

from load.schema import create_raw_schema


def _table_columns(engine, schema, table) -> set[str]:
    with engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table"
        ), {"schema": schema, "table": table})
        return {row[0] for row in result}


def test_raw_schema_exists(pg_engine):
    create_raw_schema(pg_engine)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'raw'"
        ))
        assert result.fetchone() is not None


def test_stations_table_exists(pg_engine):
    create_raw_schema(pg_engine)
    cols = _table_columns(pg_engine, "raw", "stations")
    assert cols, "raw.stations table not found"


def test_stations_table_has_required_columns(pg_engine):
    create_raw_schema(pg_engine)
    cols = _table_columns(pg_engine, "raw", "stations")
    assert {"node_id", "trading_name", "brand_name", "location",
            "amenities", "opening_times", "fuel_types", "loaded_at"}.issubset(cols)


def test_fuel_prices_table_exists(pg_engine):
    create_raw_schema(pg_engine)
    cols = _table_columns(pg_engine, "raw", "fuel_prices")
    assert cols, "raw.fuel_prices table not found"


def test_fuel_prices_table_has_required_columns(pg_engine):
    create_raw_schema(pg_engine)
    cols = _table_columns(pg_engine, "raw", "fuel_prices")
    assert {"node_id", "trading_name", "fuel_prices", "loaded_at"}.issubset(cols)


def test_fuel_prices_has_loaded_at_index(pg_engine):
    create_raw_schema(pg_engine)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT 1 FROM pg_indexes "
            "WHERE schemaname = 'raw' AND tablename = 'fuel_prices' "
            "AND indexname = 'idx_fuel_prices_loaded_at'"
        ))
        assert result.fetchone() is not None


def test_pipeline_runs_table_exists(pg_engine):
    create_raw_schema(pg_engine)
    cols = _table_columns(pg_engine, "raw", "pipeline_runs")
    assert cols, "raw.pipeline_runs table not found"


def test_pipeline_runs_table_has_required_columns(pg_engine):
    create_raw_schema(pg_engine)
    cols = _table_columns(pg_engine, "raw", "pipeline_runs")
    assert {"id", "run_started_at", "run_completed_at", "is_incremental"}.issubset(cols)
