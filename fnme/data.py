import csv
from pathlib import Path

import pandas as pd
import requests
from platformdirs import user_cache_path

from fnme.constants import ENDPOINT, HEADERS


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

    response = requests.get(ENDPOINT, headers=conditional_headers, timeout=10)
    response.raise_for_status()

    if response.status_code == 304:
        print(f"[*] Using cached data. Last modified: {cached_last_modified}")
        return pd.read_csv(csv_path), cached_last_modified

    print("[!] Cache is stale. Refreshing.")

    last_modified = response.headers.get("Last-Modified")
    csv_path.write_text(response.text, encoding="utf-8")
    timestamp_path.write_text(last_modified or "")
    return pd.read_csv(csv_path), last_modified
