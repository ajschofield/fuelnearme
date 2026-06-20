import sqlalchemy as sql

from load.ingest import ingest_stations

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
