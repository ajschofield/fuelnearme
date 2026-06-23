import pandas as pd

from fnme.core.station import process_stations, sort_stations


def make_station_dataframe():
    return pd.DataFrame(
        {
            "forecourts.trading_name": ["Near Station", "Far Station"],
            "forecourts.location.latitude": [51.5000, 51.7000],
            "forecourts.location.longitude": [-0.1000, -0.1000],
            "forecourts.fuel_price.E5": [150, 160],
            "forecourts.fuel_price.E10": [145, 155],
            "forecourts.fuel_price.B7S": [155, 165],
        }
    )


def test_process_stations_should_return_stations_within_radius():
    df = make_station_dataframe()

    stations = process_stations(df, 10, (51.5000, -0.1000))

    assert len(stations) == 1
    assert stations[0]["station_name"] == "Near Station"
    assert stations[0]["distance"] < 10


def test_process_stations_should_convert_prices_and_handle_nan():
    df = pd.DataFrame(
        {
            "forecourts.trading_name": ["Station"],
            "forecourts.location.latitude": [51.5000],
            "forecourts.location.longitude": [-0.1000],
            "forecourts.fuel_price.E5": [150],
            "forecourts.fuel_price.E10": [None],
            "forecourts.fuel_price.B7S": [165],
        }
    )

    stations = process_stations(df, 10, (51.5000, -0.1000))

    assert stations[0]["e5_price"] == 1.50
    assert stations[0]["e10_price"] is None
    assert stations[0]["diesel_price"] == 1.65


def test_sort_stations_should_sort_by_distance():
    stations = [
        {
            "station_name": "B",
            "distance": 2.0,
            "e5_price": 1.5,
            "e10_price": 1.4,
            "diesel_price": 1.6,
        },
        {
            "station_name": "A",
            "distance": 1.0,
            "e5_price": 1.4,
            "e10_price": 1.3,
            "diesel_price": 1.5,
        },
    ]

    sorted_stations = sort_stations(stations, "distance")

    assert [station["station_name"] for station in sorted_stations] == ["A", "B"]


def test_sort_stations_should_sort_with_none_last():
    stations = [
        {
            "station_name": "A",
            "distance": 1.0,
            "e5_price": None,
            "e10_price": 1.3,
            "diesel_price": 1.5,
        },
        {
            "station_name": "B",
            "distance": 2.0,
            "e5_price": 1.4,
            "e10_price": 1.2,
            "diesel_price": 1.4,
        },
    ]

    sorted_stations = sort_stations(stations, "e5")

    assert [station["station_name"] for station in sorted_stations] == ["B", "A"]