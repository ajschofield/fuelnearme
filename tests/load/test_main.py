import json

import sqlalchemy as sql

from load.main import ingest, prepare, read_secret


def test_read_secret_prefers_file_over_env(monkeypatch, tmp_path):
    secret = tmp_path / "database_url"
    secret.write_text("postgresql://from-file\n")
    monkeypatch.setenv("DATABASE_URL", "postgresql://from-env")
    monkeypatch.setenv("DATABASE_URL_FILE", str(secret))
    assert read_secret("DATABASE_URL") == "postgresql://from-file"


def test_read_secret_falls_back_to_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_FILE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://env")
    assert read_secret("DATABASE_URL") == "postgresql://env"

STATIONS = [
    {
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
]

PRICES = [
    {
        "node_id": "abc123",
        "public_phone_number": None,
        "trading_name": "Test Station",
        "fuel_prices": [
            {
                "fuel_type": "E5",
                "price": 159.9,
                "price_last_updated": "2026-02-17T16:03:04.938Z",
                "price_change_effective_timestamp": "2026-02-17T16:00:00.000Z",
            }
        ],
    }
]


def _write_input_files(data_dir, stations=STATIONS, prices=PRICES):
    (data_dir / "stations.json").write_text(json.dumps(stations))
    (data_dir / "prices.json").write_text(json.dumps(prices))


# --- prepare ---------------------------------------------------------------


def test_prepare_starts_pipeline_run_marked_full_on_first_run(pg_engine, tmp_path):
    prepare(pg_engine, tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT is_incremental FROM raw.pipeline_runs WHERE id = 1"
        ))
        assert result.fetchone()[0] is False


def test_prepare_writes_empty_watermark_on_first_run(pg_engine, tmp_path):
    prepare(pg_engine, tmp_path)
    assert (tmp_path / "watermark.txt").read_text() == ""


def test_prepare_writes_run_id_file(pg_engine, tmp_path):
    prepare(pg_engine, tmp_path)
    assert (tmp_path / "run_id.txt").read_text() == "1"


def test_prepare_second_run_is_incremental_with_watermark(pg_engine, tmp_path):
    prepare(pg_engine, tmp_path)
    _write_input_files(tmp_path)
    ingest(pg_engine, tmp_path)  # completes run 1
    prepare(pg_engine, tmp_path)  # run 2 sees a completed prior run
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT is_incremental FROM raw.pipeline_runs WHERE id = 2"
        ))
        assert result.fetchone()[0] is True
    assert (tmp_path / "watermark.txt").read_text() != ""


# --- ingest ----------------------------------------------------------------


def test_ingest_loads_stations(pg_engine, tmp_path):
    prepare(pg_engine, tmp_path)
    _write_input_files(tmp_path)
    ingest(pg_engine, tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text("SELECT COUNT(*) FROM raw.stations"))
        assert result.fetchone()[0] == 1


def test_ingest_loads_prices(pg_engine, tmp_path):
    prepare(pg_engine, tmp_path)
    _write_input_files(tmp_path)
    ingest(pg_engine, tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text("SELECT COUNT(*) FROM raw.fuel_prices"))
        assert result.fetchone()[0] == 1


def test_ingest_completes_the_pipeline_run(pg_engine, tmp_path):
    prepare(pg_engine, tmp_path)
    _write_input_files(tmp_path)
    ingest(pg_engine, tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT run_completed_at FROM raw.pipeline_runs WHERE id = 1"
        ))
        assert result.fetchone()[0] is not None
