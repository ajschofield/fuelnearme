import pandas as pd
import pytest

from fnme.core.data import get_latest_data, verify_csv_data
from fnme.exceptions import DataFetchError, InvalidDataError


def test_get_latest_data_should_not_return_empty_dataframe(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "fnme.core.data.user_cache_path",
        lambda **kwargs: tmp_path,
    )

    (tmp_path / "latest_data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "timestamp.txt").write_text(
        "Wed, 21 Oct 2020 07:28:00 GMT",
        encoding="utf-8",
    )

    class MockResponse:
        status_code = 304
        headers = {"Last-Modified": "ignored"}
        text = ""

    monkeypatch.setattr(
        "fnme.core.data.requests.get",
        lambda *args, **kwargs: MockResponse(),
    )

    df, last_modified = get_latest_data()

    assert not df.empty, "DataFrame should not be empty"
    assert last_modified == "Wed, 21 Oct 2020 07:28:00 GMT"


def test_get_latest_data_should_refresh_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "fnme.core.data.user_cache_path",
        lambda **kwargs: tmp_path,
    )

    class MockResponse:
        status_code = 200
        headers = {"Last-Modified": "Wed, 21 Oct 2020 07:28:00 GMT"}
        text = "a,b\n1,2\n"

    monkeypatch.setattr(
        "fnme.core.data.requests.get",
        lambda *args, **kwargs: MockResponse(),
    )

    df, last_modified = get_latest_data()

    assert not df.empty
    assert last_modified == "Wed, 21 Oct 2020 07:28:00 GMT"
    assert (
        (tmp_path / "latest_data.csv").read_text(encoding="utf-8")
        == "a,b\n1,2\n"
    )
    assert (
        (tmp_path / "timestamp.txt").read_text(encoding="utf-8")
        == "Wed, 21 Oct 2020 07:28:00 GMT"
    )


def test_get_latest_data_should_raise_for_request_error(monkeypatch, tmp_path):
    from fnme.core import data as data_module

    monkeypatch.setattr(
        data_module,
        "user_cache_path",
        lambda **kwargs: tmp_path,
    )

    def mock_get(*args, **kwargs):
        raise data_module.requests.RequestException("boom")

    monkeypatch.setattr(data_module.requests, "get", mock_get)

    with pytest.raises(DataFetchError):
        get_latest_data()


def test_get_latest_data_should_raise_for_bad_status(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "fnme.core.data.user_cache_path",
        lambda **kwargs: tmp_path,
    )

    class MockResponse:
        status_code = 500
        headers = {}
        text = ""

    monkeypatch.setattr(
        "fnme.core.data.requests.get",
        lambda *args, **kwargs: MockResponse(),
    )

    with pytest.raises(DataFetchError):
        get_latest_data()


def test_get_latest_data_should_retry_transient_request_failures(
    monkeypatch, tmp_path
):
    from fnme.core import data as data_module

    monkeypatch.setattr(
        data_module,
        "user_cache_path",
        lambda **kwargs: tmp_path,
    )
    monkeypatch.setattr(data_module.time, "sleep", lambda seconds: None)

    calls = {"count": 0}

    class MockResponse:
        status_code = 200
        headers = {"Last-Modified": "Wed, 21 Oct 2020 07:28:00 GMT"}
        text = "a,b\n1,2\n"

    def mock_get(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise data_module.requests.RequestException("temporary failure")
        return MockResponse()

    monkeypatch.setattr(data_module.requests, "get", mock_get)

    df, last_modified = get_latest_data()

    assert calls["count"] == 3
    assert not df.empty
    assert last_modified == "Wed, 21 Oct 2020 07:28:00 GMT"


def make_valid_dataframe():
    location_prefix = "forecourts.location."
    price_prefix = "forecourts.fuel_price."
    submission_prefix = "forecourts.price_submission_timestamp."
    change_prefix = "forecourts.price_change_effective_timestamp."
    opening_prefix = "forecourts.opening_times.usual_days."
    holiday_prefix = "forecourts.opening_times.bank_holiday.standard."
    amenities_prefix = "forecourts.amenities."
    energy_prefix = "forecourts.amenities.fuel_and_energy_services."

    return pd.DataFrame(
        {
            "forecourt_update_timestamp": ["2024-01-01 00:00:00"],
            "forecourts.node_id": [1],
            "forecourts.trading_name": ["Test Station"],
            "forecourts.brand_name": ["Test Brand"],
            "forecourts.is_motorway_service_station": [False],
            "forecourts.is_supermarket_service_station": [False],
            "forecourts.public_phone_number": ["0123456789"],
            "forecourts.temporary_closure": [False],
            "forecourts.permanent_closure": [False],
            "forecourts.permanent_closure_date": [""],
            location_prefix + "postcode": ["TE5 7ST"],
            location_prefix + "address_line_1": ["123 Test St"],
            location_prefix + "address_line_2": ["Suite 100"],
            location_prefix + "city": ["Testville"],
            location_prefix + "county": ["Testshire"],
            location_prefix + "country": ["UK"],
            location_prefix + "latitude": [51.5074],
            location_prefix + "longitude": [-0.1278],
            price_prefix + "E5": [1.5],
            submission_prefix + "E5": ["2024-01-01 00:00:00"],
            change_prefix + "E5": ["2024-01-01 00:00:00"],
            price_prefix + "E10": [1.45],
            submission_prefix + "E10": ["2024-01-01 00:00:00"],
            change_prefix + "E10": ["2024-01-01 00:00:00"],
            price_prefix + "B7S": [1.6],
            submission_prefix + "B7S": ["2024-01-01 00:00:00"],
            change_prefix + "B7S": ["2024-01-01 00:00:00"],
            price_prefix + "B7P": [1.65],
            submission_prefix + "B7P": ["2024-01-01 00:00:00"],
            change_prefix + "B7P": ["2024-01-01 00:00:00"],
            price_prefix + "B10": [1.55],
            submission_prefix + "B10": ["2024-01-01 00:00:00"],
            change_prefix + "B10": ["2024-01-01 00:00:00"],
            price_prefix + "HVO": [1.7],
            submission_prefix + "HVO": ["2024-01-01 00:00:00"],
            change_prefix + "HVO": ["2024-01-01 00:00:00"],
            opening_prefix + "monday.open_time": ["06:00"],
            opening_prefix + "monday.close_time": ["22:00"],
            opening_prefix + "monday.is_24_hours": [False],
            opening_prefix + "tuesday.open_time": ["06:00"],
            opening_prefix + "tuesday.close_time": ["22:00"],
            opening_prefix + "tuesday.is_24_hours": [False],
            opening_prefix + "wednesday.open_time": ["06:00"],
            opening_prefix + "wednesday.close_time": ["22:00"],
            opening_prefix + "wednesday.is_24_hours": [False],
            opening_prefix + "thursday.open_time": ["06:00"],
            opening_prefix + "thursday.close_time": ["22:00"],
            opening_prefix + "thursday.is_24_hours": [False],
            opening_prefix + "friday.open_time": ["06:00"],
            opening_prefix + "friday.close_time": ["22:00"],
            opening_prefix + "friday.is_24_hours": [False],
            opening_prefix + "saturday.open_time": ["08:00"],
            opening_prefix + "saturday.close_time": ["20:00"],
            opening_prefix + "saturday.is_24_hours": [False],
            opening_prefix + "sunday.open_time": ["08:00"],
            opening_prefix + "sunday.close_time": ["20:00"],
            opening_prefix + "sunday.is_24_hours": [False],
            holiday_prefix + "open_time": ["08:00"],
            holiday_prefix + "close_time": ["20:00"],
            holiday_prefix + "is_24_hours": [False],
            energy_prefix + "adblue_pumps": [False],
            energy_prefix + "adblue_packaged": [False],
            energy_prefix + "lpg_pumps": [False],
            amenities_prefix + "vehicle_services.car_wash": [True],
            amenities_prefix + "air_pump_or_screenwash": [True],
            amenities_prefix + "water_filling": [True],
            amenities_prefix + "twenty_four_hour_fuel": [False],
            amenities_prefix + "customer_toilets": [True],
        }
    )


def test_verify_csv_data_should_pass_with_valid_dataframe():
    df = make_valid_dataframe()

    assert verify_csv_data(df) is True


def test_verify_csv_data_should_fail_with_missing_column():
    df = make_valid_dataframe().drop(columns=["forecourts.location.country"])

    with pytest.raises(InvalidDataError):
        verify_csv_data(df)


def test_verify_csv_data_should_fail_with_extra_column():
    df = make_valid_dataframe()
    df["extra.column"] = ["value"]

    with pytest.raises(InvalidDataError):
        verify_csv_data(df)

