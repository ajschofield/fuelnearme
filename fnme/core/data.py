import csv
from pathlib import Path

import pandas as pd
import requests
from platformdirs import user_cache_path

from fnme.constants import ENDPOINT, HEADERS
from fnme.exceptions import DataFetchError


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

    try:
        response = requests.get(
            ENDPOINT, headers=conditional_headers, timeout=10
        )
    except requests.RequestException as e:
        raise DataFetchError(message=f"GET request failed: {e}")

    if response.status_code == 304:
        print(f"[*] Using cached data. Last modified: {cached_last_modified}")
        return pd.read_csv(csv_path), cached_last_modified

    if response.status_code != 200:
        raise DataFetchError(
            message=f"Failed to fetch data. Status code: {response.status_code}"
        )

    print("[!] Cache is stale. Refreshing.")

    last_modified = response.headers.get("Last-Modified")

    try:
        csv_path.write_text(response.text, encoding="utf-8")
    except Exception as e:
        raise DataFetchError(message=f"Error writing CSV cache: {e}")
    try:
        timestamp_path.write_text(last_modified or "")
    except Exception as e:
        raise DataFetchError(message=f"Error writing timestamp file: {e}")

    return pd.read_csv(csv_path), last_modified
