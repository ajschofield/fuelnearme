import json

import sqlalchemy as sql

from load.main import main

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


def _write_input_files(tmp_path, stations=STATIONS, prices=PRICES):
    (tmp_path / "stations.json").write_text(json.dumps(stations))
    (tmp_path / "prices.json").write_text(json.dumps(prices))


def test_main_ingests_stations(pg_engine, tmp_path):
    _write_input_files(tmp_path)
    main(engine=pg_engine, input_dir=tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text("SELECT COUNT(*) FROM raw.stations"))
        assert result.fetchone()[0] == 1


def test_main_ingests_prices(pg_engine, tmp_path):
    _write_input_files(tmp_path)
    main(engine=pg_engine, input_dir=tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text("SELECT COUNT(*) FROM raw.fuel_prices"))
        assert result.fetchone()[0] == 1


def test_main_records_completed_pipeline_run(pg_engine, tmp_path):
    _write_input_files(tmp_path)
    main(engine=pg_engine, input_dir=tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT run_completed_at FROM raw.pipeline_runs WHERE id = 1"
        ))
        assert result.fetchone()[0] is not None


def test_main_marks_full_run_as_not_incremental(pg_engine, tmp_path):
    _write_input_files(tmp_path)
    main(engine=pg_engine, input_dir=tmp_path)
    with pg_engine.connect() as conn:
        result = conn.execute(sql.text(
            "SELECT is_incremental FROM raw.pipeline_runs WHERE id = 1"
        ))
        assert result.fetchone()[0] is False
