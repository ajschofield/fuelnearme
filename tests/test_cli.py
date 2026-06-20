import argparse

import pandas as pd
import pytest

from fnme import cli
from fnme.exceptions import DataFetchError, InvalidDataError, LocationError


def test_parse_args_should_parse_required_arguments(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["fnme", "-a", "LS11"],
    )

    args = cli.parse_args()

    assert args.address == "LS11"
    assert args.radius == 5
    assert args.sort == "e10"


def test_fmt_price_should_return_na_for_none():
    assert cli._fmt_price(None) == "N/A"


def test_fmt_price_should_format_float_to_two_decimals():
    assert cli._fmt_price(1.234) == "1.23"


def test_output_stations_should_print_no_stations_message(capsys):
    cli.output_stations([])

    captured = capsys.readouterr()
    assert "[*] No stations found." in captured.out


def test_output_stations_should_format_rows(monkeypatch):
    captured = {}

    def fake_tabulate(rows, headers, floatfmt):
        captured["rows"] = rows
        captured["headers"] = headers
        captured["floatfmt"] = floatfmt
        return "table"

    monkeypatch.setattr(cli, "tabulate", fake_tabulate)

    cli.output_stations(
        [
            {
                "station_name": "Station A",
                "distance": 1.2,
                "e5_price": 1.234,
                "e10_price": 1.345,
                "diesel_price": 1.456,
            }
        ]
    )

    assert captured["rows"][0]["e5_price"] == "1.23"
    assert captured["rows"][0]["e10_price"] == "1.34"
    assert captured["rows"][0]["diesel_price"] == "1.46"
    assert captured["floatfmt"] == ".1f"


def test_main_should_run_happy_path(monkeypatch):
    args = argparse.Namespace(address="LS11", radius=5, sort="distance")
    df = pd.DataFrame(
        {
            "forecourts.trading_name": ["Station A"],
            "forecourts.location.latitude": [51.5],
            "forecourts.location.longitude": [-0.1],
            "forecourts.fuel_price.E5": [150],
            "forecourts.fuel_price.E10": [145],
            "forecourts.fuel_price.B7S": [155],
        }
    )
    stations = [
        {
            "station_name": "Station A",
            "distance": 1.0,
            "e5_price": 1.5,
            "e10_price": 1.45,
            "diesel_price": 1.55,
        }
    ]
    captured = {}

    monkeypatch.setattr(cli, "parse_args", lambda: args)
    monkeypatch.setattr(cli, "get_location", lambda address: (51.5, -0.1))
    monkeypatch.setattr(
        cli,
        "get_latest_data",
        lambda: (df, "Wed, 21 Oct 2020 07:28:00 GMT"),
    )
    monkeypatch.setattr(cli, "verify_csv_data", lambda data: True)
    monkeypatch.setattr(
        cli,
        "process_stations",
        lambda data, radius, location: stations,
    )
    monkeypatch.setattr(cli, "sort_stations", lambda items, sort: items)
    monkeypatch.setattr(
        cli,
        "output_stations",
        lambda items: captured.setdefault("items", items),
    )

    cli.main()

    assert captured["items"] == stations


def test_main_should_exit_for_location_error(monkeypatch, capsys):
    args = argparse.Namespace(address="LS11", radius=5, sort="distance")

    monkeypatch.setattr(cli, "parse_args", lambda: args)
    monkeypatch.setattr(
        cli,
        "get_location",
        lambda address: (_ for _ in ()).throw(LocationError("bad address")),
    )

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "Error: bad address" in captured.out


def test_main_should_exit_for_data_fetch_error(monkeypatch, capsys):
    args = argparse.Namespace(address="LS11", radius=5, sort="distance")

    monkeypatch.setattr(cli, "parse_args", lambda: args)
    monkeypatch.setattr(cli, "get_location", lambda address: (51.5, -0.1))
    monkeypatch.setattr(
        cli,
        "get_latest_data",
        lambda: (_ for _ in ()).throw(DataFetchError("no data")),
    )

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "Error: no data" in captured.out


def test_main_should_exit_for_invalid_data_error(monkeypatch, capsys):
    args = argparse.Namespace(address="LS11", radius=5, sort="distance")
    df = pd.DataFrame({"forecourts.trading_name": ["Station A"]})

    monkeypatch.setattr(cli, "parse_args", lambda: args)
    monkeypatch.setattr(cli, "get_location", lambda address: (51.5, -0.1))
    monkeypatch.setattr(
        cli,
        "get_latest_data",
        lambda: (df, "Wed, 21 Oct 2020 07:28:00 GMT"),
    )
    monkeypatch.setattr(
        cli,
        "verify_csv_data",
        lambda data: (_ for _ in ()).throw(InvalidDataError("bad schema")),
    )

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "Error: bad schema" in captured.out