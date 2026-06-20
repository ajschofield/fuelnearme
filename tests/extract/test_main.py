import json
from pathlib import Path
from unittest.mock import patch

from extract.main import main

STATIONS = [{"node_id": "abc123", "trading_name": "Test Station"}]
PRICES = [{"node_id": "abc123", "trading_name": "Test Station", "fuel_prices": []}]


@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_writes_stations_json(mock_stations, mock_prices, tmp_path):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path)
    data = json.loads((tmp_path / "stations.json").read_text())
    assert data == STATIONS


@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_writes_prices_json(mock_stations, mock_prices, tmp_path):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path)
    data = json.loads((tmp_path / "prices.json").read_text())
    assert data == PRICES


@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_passes_timestamp_to_fetchers(mock_stations, mock_prices, tmp_path):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path, effective_start_timestamp="2026-06-01 00:00:00")
    mock_stations.assert_called_once_with(effective_start_timestamp="2026-06-01 00:00:00")
    mock_prices.assert_called_once_with(effective_start_timestamp="2026-06-01 00:00:00")


@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_passes_no_timestamp_when_none(mock_stations, mock_prices, tmp_path):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path)
    mock_stations.assert_called_once_with(effective_start_timestamp=None)
    mock_prices.assert_called_once_with(effective_start_timestamp=None)
