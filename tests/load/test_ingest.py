import sqlalchemy as sql

from load.ingest import (
    complete_pipeline_run,
    ingest_prices,
    ingest_stations,
    start_pipeline_run,
)

STATION_1 = {
    "node_id": "abc123",
    "public_phone_number": None,
    "trading_name": "Test Station",
    "is_same_trading_and_brand_name": True,
    "brand_name": "Test Brand",
    "temporary_closure": False,
    "permanent_closure": False,
    "permanent_closure_date": None,
    "is_motorway_service_station": False,
    "is_supermarket_service_station": False,
    "location": {"postcode": "LS1 1AA", "latitude": 53.7997, "longitude": -1.5492},
    "amenities": ["car_wash"],
    "opening_times": {},
    "fuel_types": ["E5", "E10"],
}

STATION_2 = {
    **STATION_1,
    "node_id": "def456",
    "trading_name": "Second Station",
}


def test_ingest_stations_returns_count(pg_engine):
    count = ingest_stations(pg_engine, [STATION_1, STATION_2])
    assert count == 2


def test_ingest_stations_persists_records(pg_engine):
    ingest_stations(pg_engine, [STATION_1])
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT trading_name FROM raw.stations WHERE node_id = :id"
        ), {"id": STATION_1["node_id"]})
        assert result.fetchone()[0] == "Test Station"


def test_ingest_stations_upserts_on_conflict(pg_engine):
    ingest_stations(pg_engine, [STATION_1])
    updated = {**STATION_1, "trading_name": "Renamed Station"}
    ingest_stations(pg_engine, [updated])
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT COUNT(*), MAX(trading_name) FROM raw.stations WHERE node_id = :id"
        ), {"id": STATION_1["node_id"]})
        row = result.fetchone()
        assert row[0] == 1
        assert row[1] == "Renamed Station"


def test_ingest_stations_empty_list_returns_zero(pg_engine):
    assert ingest_stations(pg_engine, []) == 0


PRICE_1 = {
    "node_id": "abc123",
    "public_phone_number": None,
    "trading_name": "Test Station",
    "fuel_prices": [
        {
            "fuel_type": "E5",
            "price": 159.9,
            "price_last_updated": "2026-02-17T16:03:04.938Z",
            "price_change_effective_timestamp": "2026-02-17T16:00:00.000Z",
        },
        {
            "fuel_type": "E10",
            "price": 132.9,
            "price_last_updated": "2026-02-17T16:03:04.938Z",
            "price_change_effective_timestamp": "2026-02-17T16:00:00.000Z",
        },
    ],
}

PRICE_2 = {
    **PRICE_1,
    "node_id": "def456",
    "trading_name": "Second Station",
}


def test_ingest_prices_returns_count(pg_engine):
    count = ingest_prices(pg_engine, [PRICE_1, PRICE_2])
    assert count == 2


def test_ingest_prices_persists_records(pg_engine):
    ingest_prices(pg_engine, [PRICE_1])
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT trading_name FROM raw.fuel_prices WHERE node_id = :id"
        ), {"id": PRICE_1["node_id"]})
        assert result.fetchone()[0] == "Test Station"


def test_ingest_prices_appends_on_repeat(pg_engine):
    ingest_prices(pg_engine, [PRICE_1])
    ingest_prices(pg_engine, [PRICE_1])
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT COUNT(*) FROM raw.fuel_prices WHERE node_id = :id"
        ), {"id": PRICE_1["node_id"]})
        assert result.fetchone()[0] == 2


def test_ingest_prices_empty_list_returns_zero(pg_engine):
    assert ingest_prices(pg_engine, []) == 0


def test_start_pipeline_run_returns_integer_id(pg_engine):
    run_id = start_pipeline_run(pg_engine, is_incremental=False)
    assert isinstance(run_id, int) and run_id > 0


def test_start_pipeline_run_records_is_incremental(pg_engine):
    run_id = start_pipeline_run(pg_engine, is_incremental=True)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT is_incremental FROM raw.pipeline_runs WHERE id = :id"
        ), {"id": run_id})
        assert result.fetchone()[0] is True


def test_start_pipeline_run_leaves_completed_at_null(pg_engine):
    run_id = start_pipeline_run(pg_engine, is_incremental=False)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT run_completed_at FROM raw.pipeline_runs WHERE id = :id"
        ), {"id": run_id})
        assert result.fetchone()[0] is None


def test_complete_pipeline_run_sets_completed_at(pg_engine):
    run_id = start_pipeline_run(pg_engine, is_incremental=False)
    complete_pipeline_run(pg_engine, run_id)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT run_completed_at FROM raw.pipeline_runs WHERE id = :id"
        ), {"id": run_id})
        assert result.fetchone()[0] is not None
