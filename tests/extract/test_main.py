import json
from unittest.mock import patch

import pytest

from extract.main import main, read_secret

STATIONS = [{"node_id": "abc123", "trading_name": "Test Station"}]
PRICES = [{"node_id": "abc123", "trading_name": "Test Station", "fuel_prices": []}]
TOKEN = "mock_access_token"


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_writes_stations_json(mock_stations, mock_prices, mock_token, tmp_path):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path, client_id="id", client_secret="secret")
    data = json.loads((tmp_path / "stations.json").read_text())
    assert data == STATIONS


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_writes_prices_json(mock_stations, mock_prices, mock_token, tmp_path):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path, client_id="id", client_secret="secret")
    data = json.loads((tmp_path / "prices.json").read_text())
    assert data == PRICES


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_generates_token_with_credentials(
    mock_stations, mock_prices, mock_token, tmp_path
):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path, client_id="my_id", client_secret="my_secret")
    mock_token.assert_called_once_with("my_id", "my_secret")


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_passes_token_and_timestamp_to_fetchers(
    mock_stations, mock_prices, mock_token, tmp_path
):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(
        output_dir=tmp_path,
        effective_start_timestamp="2026-06-01 00:00:00",
        client_id="id",
        client_secret="secret",
    )
    mock_stations.assert_called_once_with(
        TOKEN, effective_start_timestamp="2026-06-01 00:00:00"
    )
    mock_prices.assert_called_once_with(
        TOKEN, effective_start_timestamp="2026-06-01 00:00:00"
    )


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_passes_no_timestamp_when_none(
    mock_stations, mock_prices, mock_token, tmp_path
):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    main(output_dir=tmp_path, client_id="id", client_secret="secret")
    mock_stations.assert_called_once_with(TOKEN, effective_start_timestamp=None)
    mock_prices.assert_called_once_with(TOKEN, effective_start_timestamp=None)


def test_read_secret_from_env(monkeypatch):
    monkeypatch.delenv("MY_SECRET_FILE", raising=False)
    monkeypatch.setenv("MY_SECRET", "from-env")
    assert read_secret("MY_SECRET") == "from-env"


def test_read_secret_from_file(monkeypatch, tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("from-file\n")
    monkeypatch.setenv("MY_SECRET_FILE", str(secret))
    assert read_secret("MY_SECRET") == "from-file"


def test_read_secret_file_takes_precedence_over_env(monkeypatch, tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("file-wins")
    monkeypatch.setenv("MY_SECRET", "env-loses")
    monkeypatch.setenv("MY_SECRET_FILE", str(secret))
    assert read_secret("MY_SECRET") == "file-wins"


def test_read_secret_missing_raises(monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    monkeypatch.delenv("NOPE_FILE", raising=False)
    with pytest.raises(KeyError):
        read_secret("NOPE")


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_reads_timestamp_from_watermark_file(
    mock_stations, mock_prices, mock_token, tmp_path
):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    (tmp_path / "watermark.txt").write_text("2026-06-01T00:00:00")
    main(output_dir=tmp_path, client_id="id", client_secret="secret")
    mock_stations.assert_called_once_with(
        TOKEN, effective_start_timestamp="2026-06-01T00:00:00"
    )
    mock_prices.assert_called_once_with(
        TOKEN, effective_start_timestamp="2026-06-01T00:00:00"
    )


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_empty_watermark_file_means_full_run(
    mock_stations, mock_prices, mock_token, tmp_path
):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    (tmp_path / "watermark.txt").write_text("")
    main(output_dir=tmp_path, client_id="id", client_secret="secret")
    mock_stations.assert_called_once_with(TOKEN, effective_start_timestamp=None)


@patch("extract.main.generate_access_token", return_value=TOKEN)
@patch("extract.main.fetch_all_prices")
@patch("extract.main.fetch_all_stations")
def test_main_explicit_timestamp_overrides_watermark_file(
    mock_stations, mock_prices, mock_token, tmp_path
):
    mock_stations.return_value = STATIONS
    mock_prices.return_value = PRICES
    (tmp_path / "watermark.txt").write_text("2026-06-01T00:00:00")
    main(
        output_dir=tmp_path,
        effective_start_timestamp="2026-01-01T00:00:00",
        client_id="id",
        client_secret="secret",
    )
    mock_stations.assert_called_once_with(
        TOKEN, effective_start_timestamp="2026-01-01T00:00:00"
    )
