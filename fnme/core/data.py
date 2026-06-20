import os
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests
from platformdirs import user_cache_path

from fnme.constants import ENDPOINT, HEADERS
from fnme.exceptions import DataFetchError, InvalidDataError

_FETCH_RETRIES = 3


def _atomic_write_text(path: Path, text: str) -> None:
    tmp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as tmp_file:
            tmp_file.write(text)
            tmp_path = Path(tmp_file.name)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def get_latest_data() -> tuple[pd.DataFrame, str | None]:
    cache_dir = Path(user_cache_path(appname="fnme", appauthor=False))
    csv_path = cache_dir / "latest_data.csv"
    timestamp_path = cache_dir / "timestamp.txt"

    cache_dir.mkdir(parents=True, exist_ok=True)

    cached_last_modified = (
        timestamp_path.read_text() if timestamp_path.exists() else None
    )

    conditional_headers = {
        **HEADERS,
        **(
            {"If-Modified-Since": cached_last_modified}
            if cached_last_modified and csv_path.exists()
            else {}
        ),
    }

    response = None
    last_error: Exception | None = None

    for attempt in range(_FETCH_RETRIES):
        try:
            response = requests.get(
                ENDPOINT, headers=conditional_headers, timeout=10
            )
            if response.status_code < 500:
                break
        except requests.RequestException as e:
            last_error = e
        else:
            if response.status_code < 500:
                break
            last_error = DataFetchError(
                message=(
                    f"Failed to fetch data. Status code: "
                    f"{response.status_code}"
                )
            )

        if attempt < _FETCH_RETRIES - 1:
            time.sleep(2**attempt)

    if response is None:
        raise DataFetchError(message=f"GET request failed: {last_error}")

    if response.status_code == 304:
        print(f"[*] Using cached data. Last modified: {cached_last_modified}")
        return pd.read_csv(csv_path), cached_last_modified

    if response.status_code != 200:
        raise DataFetchError(
            message=(
                f"Failed to fetch data. Status code: {response.status_code}"
            )
        )

    print("[!] Cache is stale. Refreshing.")

    last_modified = response.headers.get("Last-Modified")

    try:
        _atomic_write_text(csv_path, response.text)
    except Exception as e:
        raise DataFetchError(message=f"Error writing CSV cache: {e}")
    try:
        _atomic_write_text(timestamp_path, last_modified or "")
    except Exception as e:
        raise DataFetchError(message=f"Error writing timestamp file: {e}")

    return pd.read_csv(csv_path), last_modified


def verify_csv_data(df: pd.DataFrame) -> None:
    required_columns = sorted([
        "forecourt_update_timestamp",
        "forecourts.node_id",
        "forecourts.trading_name",
        "forecourts.brand_name",
        "forecourts.is_motorway_service_station",
        "forecourts.is_supermarket_service_station",
        "forecourts.public_phone_number",
        "forecourts.temporary_closure",
        "forecourts.permanent_closure",
        "forecourts.permanent_closure_date",
        "forecourts.location.postcode",
        "forecourts.location.address_line_1",
        "forecourts.location.address_line_2",
        "forecourts.location.city",
        "forecourts.location.county",
        "forecourts.location.country",
        "forecourts.location.latitude",
        "forecourts.location.longitude",
        "forecourts.fuel_price.E5",
        "forecourts.price_submission_timestamp.E5",
        "forecourts.price_change_effective_timestamp.E5",
        "forecourts.fuel_price.E10",
        "forecourts.price_submission_timestamp.E10",
        "forecourts.price_change_effective_timestamp.E10",
        "forecourts.fuel_price.B7S",
        "forecourts.price_submission_timestamp.B7S",
        "forecourts.price_change_effective_timestamp.B7S",
        "forecourts.fuel_price.B7P",
        "forecourts.price_submission_timestamp.B7P",
        "forecourts.price_change_effective_timestamp.B7P",
        "forecourts.fuel_price.B10",
        "forecourts.price_submission_timestamp.B10",
        "forecourts.price_change_effective_timestamp.B10",
        "forecourts.fuel_price.HVO",
        "forecourts.price_submission_timestamp.HVO",
        "forecourts.price_change_effective_timestamp.HVO",
        "forecourts.opening_times.usual_days.monday.open_time",
        "forecourts.opening_times.usual_days.monday.close_time",
        "forecourts.opening_times.usual_days.monday.is_24_hours",
        "forecourts.opening_times.usual_days.tuesday.open_time",
        "forecourts.opening_times.usual_days.tuesday.close_time",
        "forecourts.opening_times.usual_days.tuesday.is_24_hours",
        "forecourts.opening_times.usual_days.wednesday.open_time",
        "forecourts.opening_times.usual_days.wednesday.close_time",
        "forecourts.opening_times.usual_days.wednesday.is_24_hours",
        "forecourts.opening_times.usual_days.thursday.open_time",
        "forecourts.opening_times.usual_days.thursday.close_time",
        "forecourts.opening_times.usual_days.thursday.is_24_hours",
        "forecourts.opening_times.usual_days.friday.open_time",
        "forecourts.opening_times.usual_days.friday.close_time",
        "forecourts.opening_times.usual_days.friday.is_24_hours",
        "forecourts.opening_times.usual_days.saturday.open_time",
        "forecourts.opening_times.usual_days.saturday.close_time",
        "forecourts.opening_times.usual_days.saturday.is_24_hours",
        "forecourts.opening_times.usual_days.sunday.open_time",
        "forecourts.opening_times.usual_days.sunday.close_time",
        "forecourts.opening_times.usual_days.sunday.is_24_hours",
        "forecourts.opening_times.bank_holiday.standard.open_time",
        "forecourts.opening_times.bank_holiday.standard.close_time",
        "forecourts.opening_times.bank_holiday.standard.is_24_hours",
        "forecourts.amenities.fuel_and_energy_services.adblue_pumps",
        "forecourts.amenities.fuel_and_energy_services.adblue_packaged",
        "forecourts.amenities.fuel_and_energy_services.lpg_pumps",
        "forecourts.amenities.vehicle_services.car_wash",
        "forecourts.amenities.air_pump_or_screenwash",
        "forecourts.amenities.water_filling",
        "forecourts.amenities.twenty_four_hour_fuel",
        "forecourts.amenities.customer_toilets",
    ])

    columns_in_df = sorted(list(df.columns))

    if required_columns != columns_in_df:
        required_set = set(required_columns)
        columns_set = set(columns_in_df)
        raise InvalidDataError(
            message=(
                "DataFrame columns do not match the expected schema. "
                f"Missing columns: {sorted(required_set - columns_set)}, "
                f"Extra columns: {sorted(columns_set - required_set)}"
            )
        )

    return True
