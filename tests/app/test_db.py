import sqlalchemy as sql

from app.db import get_all_fuel_averages, get_latest_prices, get_nearby_stations

LEEDS_LAT, LEEDS_LON = 53.7997, -1.5492
MANCHESTER_LAT, MANCHESTER_LON = 53.4808, -2.2426


def _insert_price(conn, node_id, trading_name, fuel_type, price_pence,
                  lat, lon, postcode, loaded_at="2026-06-01 00:00:00+00"):
    conn.execute(sql.text("""
        INSERT INTO marts.fct_fuel_prices
            (node_id, trading_name, fuel_type, price_pence,
             latitude, longitude, postcode, city, loaded_at,
             is_motorway_service_station, is_supermarket_service_station)
        VALUES
            (:node_id, :trading_name, :fuel_type, :price_pence,
             :lat, :lon, :postcode, 'Leeds', :loaded_at, false, false)
    """), dict(node_id=node_id, trading_name=trading_name, fuel_type=fuel_type,
               price_pence=price_pence, lat=lat, lon=lon,
               postcode=postcode, loaded_at=loaded_at))


def test_get_latest_prices_returns_rows(app_engine):
    with app_engine.connect() as conn:
        _insert_price(conn, "abc123", "Test Station", "E10", 132.9,
                      LEEDS_LAT, LEEDS_LON, "LS1 1AA")
        conn.commit()
    result = get_latest_prices(app_engine, fuel_type="E10")
    assert len(result) == 1
    assert result[0]["node_id"] == "abc123"


def test_get_latest_prices_returns_only_most_recent(app_engine):
    with app_engine.connect() as conn:
        _insert_price(conn, "abc123", "Test Station", "E10", 132.9,
                      LEEDS_LAT, LEEDS_LON, "LS1 1AA",
                      loaded_at="2026-06-01 00:00:00+00")
        _insert_price(conn, "abc123", "Test Station", "E10", 129.9,
                      LEEDS_LAT, LEEDS_LON, "LS1 1AA",
                      loaded_at="2026-06-10 00:00:00+00")
        conn.commit()
    result = get_latest_prices(app_engine, fuel_type="E10")
    assert len(result) == 1
    assert float(result[0]["price_pence"]) == 129.9


def test_get_all_fuel_averages_returns_per_fuel_stats(app_engine):
    with app_engine.connect() as conn:
        _insert_price(conn, "a", "S A", "E10", 150.0, LEEDS_LAT, LEEDS_LON, "LS1 1AA")
        _insert_price(conn, "b", "S B", "E10", 160.0, LEEDS_LAT, LEEDS_LON, "LS1 1BB")
        _insert_price(conn, "c", "S C", "E5",  165.0, LEEDS_LAT, LEEDS_LON, "LS1 1CC")
        conn.commit()
    result = get_all_fuel_averages(app_engine)
    assert "E10" in result
    assert float(result["E10"]["avg_pence"]) == 155.0
    assert result["E10"]["stations"] == 2
    assert "E5" in result
    assert "HVO" not in result


def test_get_all_fuel_averages_excludes_outliers(app_engine):
    with app_engine.connect() as conn:
        _insert_price(conn, "good", "Good", "E10", 149.9, LEEDS_LAT, LEEDS_LON, "LS1 1AA")
        _insert_price(conn, "bad",  "Bad",  "E10", 1.3,   LEEDS_LAT, LEEDS_LON, "LS1 1BB")
        conn.commit()
    result = get_all_fuel_averages(app_engine)
    assert float(result["E10"]["avg_pence"]) == 149.9
    assert result["E10"]["stations"] == 1


def test_get_latest_prices_excludes_outlier_prices(app_engine):
    with app_engine.connect() as conn:
        _insert_price(conn, "good", "Good Station", "E10", 149.9,
                      LEEDS_LAT, LEEDS_LON, "LS1 1AA")
        _insert_price(conn, "low", "Bogus Low", "E10", 1.3,
                      LEEDS_LAT, LEEDS_LON, "LS1 1BB")
        _insert_price(conn, "high", "Bogus High", "E10", 999.0,
                      LEEDS_LAT, LEEDS_LON, "LS1 1CC")
        conn.commit()
    result = get_latest_prices(app_engine, fuel_type="E10")
    node_ids = {r["node_id"] for r in result}
    assert "good" in node_ids
    assert "low" not in node_ids
    assert "high" not in node_ids


def test_get_nearby_stations_returns_stations_within_radius(app_engine):
    with app_engine.connect() as conn:
        _insert_price(conn, "abc123", "Leeds Station", "E10", 132.9,
                      LEEDS_LAT, LEEDS_LON, "LS1 1AA")
        _insert_price(conn, "def456", "Manchester Station", "E10", 131.9,
                      MANCHESTER_LAT, MANCHESTER_LON, "M1 1AA")
        conn.commit()
    result = get_nearby_stations(app_engine, LEEDS_LAT, LEEDS_LON, radius_miles=10)
    node_ids = {r["node_id"] for r in result}
    assert "abc123" in node_ids
    assert "def456" not in node_ids


def test_get_nearby_stations_returns_all_fuel_types(app_engine):
    with app_engine.connect() as conn:
        _insert_price(conn, "abc123", "Leeds Station", "E10", 132.9,
                      LEEDS_LAT, LEEDS_LON, "LS1 1AA")
        _insert_price(conn, "abc123", "Leeds Station", "E5", 145.9,
                      LEEDS_LAT, LEEDS_LON, "LS1 1AA")
        conn.commit()
    result = get_nearby_stations(app_engine, LEEDS_LAT, LEEDS_LON, radius_miles=10)
    fuel_types = {r["fuel_type"] for r in result}
    assert "E10" in fuel_types
    assert "E5" in fuel_types
