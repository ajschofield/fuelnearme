from unittest.mock import MagicMock, patch

import pytest

from extract.fetch import (
    fetch_all_prices,
    fetch_all_stations,
    fetch_prices_batch,
    fetch_stations_batch,
)

STATIONS_BATCH = [
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
        "location": {
            "address_line_1": "1 Test Street",
            "address_line_2": None,
            "city": "Leeds",
            "country": "England",
            "county": "West Yorkshire",
            "postcode": "LS1 1AA",
            "latitude": 53.7997,
            "longitude": -1.5492,
        },
        "amenities": ["car_wash", "customer_toilets"],
        "opening_times": {},
        "fuel_types": ["E5", "E10"],
    }
]

PRICES_BATCH = [
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
            },
            {
                "fuel_type": "E10",
                "price": 132.9,
                "price_last_updated": "2026-02-17T16:03:04.938Z",
                "price_change_effective_timestamp": "2026-02-17T16:00:00.000Z",
            },
        ],
    }
]


@patch("extract.fetch.requests.get")
def test_fetch_stations_batch_calls_correct_url(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: STATIONS_BATCH)
    fetch_stations_batch(1)
    url = mock_get.call_args[0][0]
    assert url == "https://www.fuel-finder.service.gov.uk/api/v1/pfs"


@patch("extract.fetch.requests.get")
def test_fetch_stations_batch_sends_batch_number(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: STATIONS_BATCH)
    fetch_stations_batch(1)
    params = mock_get.call_args[1]["params"]
    assert params["batch-number"] == 1


@patch("extract.fetch.requests.get")
def test_fetch_stations_batch_returns_parsed_json(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: STATIONS_BATCH)
    result = fetch_stations_batch(1)
    assert result == STATIONS_BATCH


@patch("extract.fetch.requests.get")
def test_fetch_prices_batch_calls_correct_url(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: PRICES_BATCH)
    fetch_prices_batch(1)
    url = mock_get.call_args[0][0]
    assert url == "https://www.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices"


@patch("extract.fetch.requests.get")
def test_fetch_prices_batch_sends_batch_number(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: PRICES_BATCH)
    fetch_prices_batch(1)
    params = mock_get.call_args[1]["params"]
    assert params["batch-number"] == 1


@patch("extract.fetch.requests.get")
def test_fetch_prices_batch_returns_parsed_json(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: PRICES_BATCH)
    result = fetch_prices_batch(1)
    assert result == PRICES_BATCH


@patch("extract.fetch.requests.get")
def test_fetch_stations_batch_raises_on_http_error(mock_get):
    mock_get.return_value = MagicMock(status_code=500)
    with pytest.raises(RuntimeError):
        fetch_stations_batch(1)


@patch("extract.fetch.requests.get")
def test_fetch_prices_batch_raises_on_http_error(mock_get):
    mock_get.return_value = MagicMock(status_code=500)
    with pytest.raises(RuntimeError):
        fetch_prices_batch(1)


STATIONS_BATCH_2 = [
    {
        "node_id": "def456",
        "public_phone_number": "+441234567890",
        "trading_name": "Second Station",
        "is_same_trading_and_brand_name": False,
        "brand_name": "Other Brand",
        "temporary_closure": False,
        "permanent_closure": False,
        "permanent_closure_date": None,
        "is_motorway_service_station": True,
        "is_supermarket_service_station": False,
        "location": {
            "address_line_1": "2 Test Road",
            "address_line_2": None,
            "city": "Manchester",
            "country": "England",
            "county": "Greater Manchester",
            "postcode": "M1 1AA",
            "latitude": 53.4808,
            "longitude": -2.2426,
        },
        "amenities": ["adblue_pumps"],
        "opening_times": {},
        "fuel_types": ["E5", "B7_STANDARD"],
    }
]

PRICES_BATCH_2 = [
    {
        "node_id": "def456",
        "public_phone_number": "+441234567890",
        "trading_name": "Second Station",
        "fuel_prices": [
            {
                "fuel_type": "E5",
                "price": 155.9,
                "price_last_updated": "2026-02-17T16:03:04.938Z",
                "price_change_effective_timestamp": "2026-02-17T16:00:00.000Z",
            },
        ],
    }
]


@patch("extract.fetch.requests.get")
def test_fetch_all_stations_combines_batches(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: STATIONS_BATCH),
        MagicMock(status_code=200, json=lambda: STATIONS_BATCH_2),
        MagicMock(status_code=200, json=lambda: []),
    ]
    result = fetch_all_stations()
    assert result == STATIONS_BATCH + STATIONS_BATCH_2


@patch("extract.fetch.requests.get")
def test_fetch_all_stations_stops_on_empty_batch(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: STATIONS_BATCH),
        MagicMock(status_code=200, json=lambda: []),
    ]
    fetch_all_stations()
    assert mock_get.call_count == 2


@patch("extract.fetch.requests.get")
def test_fetch_all_prices_combines_batches(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: PRICES_BATCH),
        MagicMock(status_code=200, json=lambda: PRICES_BATCH_2),
        MagicMock(status_code=200, json=lambda: []),
    ]
    result = fetch_all_prices()
    assert result == PRICES_BATCH + PRICES_BATCH_2


@patch("extract.fetch.requests.get")
def test_fetch_all_prices_stops_on_empty_batch(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: PRICES_BATCH),
        MagicMock(status_code=200, json=lambda: []),
    ]
    fetch_all_prices()
    assert mock_get.call_count == 2


@patch("extract.fetch.requests.get")
def test_fetch_all_stations_passes_timestamp(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: STATIONS_BATCH),
        MagicMock(status_code=200, json=lambda: []),
    ]
    fetch_all_stations(effective_start_timestamp="2026-06-01 00:00:00")
    params = mock_get.call_args_list[0][1]["params"]
    assert params["effective-start-timestamp"] == "2026-06-01 00:00:00"


@patch("extract.fetch.requests.get")
def test_fetch_all_prices_passes_timestamp(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: PRICES_BATCH),
        MagicMock(status_code=200, json=lambda: []),
    ]
    fetch_all_prices(effective_start_timestamp="2026-06-01 00:00:00")
    params = mock_get.call_args_list[0][1]["params"]
    assert params["effective-start-timestamp"] == "2026-06-01 00:00:00"


@patch("extract.fetch.requests.get")
def test_fetch_all_stations_omits_timestamp_when_none(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: STATIONS_BATCH),
        MagicMock(status_code=200, json=lambda: []),
    ]
    fetch_all_stations()
    params = mock_get.call_args_list[0][1]["params"]
    assert "effective-start-timestamp" not in params


@patch("extract.fetch.requests.get")
def test_fetch_all_prices_omits_timestamp_when_none(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: PRICES_BATCH),
        MagicMock(status_code=200, json=lambda: []),
    ]
    fetch_all_prices()
    params = mock_get.call_args_list[0][1]["params"]
    assert "effective-start-timestamp" not in params
