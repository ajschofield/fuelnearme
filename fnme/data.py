import os
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from platformdirs import user_cache_path

from fnme.constants import ENDPOINT, HEADERS


def get_latest_data() -> tuple[pd.DataFrame, str | None]:
    cache_dir = Path(user_cache_path(appname="fnme", appauthor=False))
    csv_path = cache_dir / "latest_data.csv"
    timestamp_path = cache_dir / "timestamp.txt"

    cache_dir.mkdir(parents=True, exist_ok=True)

    remote_last_modified = requests.head(
        ENDPOINT, headers=HEADERS, timeout=10
    ).headers.get("Last-Modified")

    cached_last_modified = (
        timestamp_path.read_text() if timestamp_path.exists() else None
    )

    if not csv_path.exists() or remote_last_modified != cached_last_modified:
        response = requests.get(ENDPOINT, headers=HEADERS, timeout=10)
        response.raise_for_status()
        last_modified = response.headers.get("Last-Modified")
        csv_path.write_text(response.text, encoding="utf-8")
        timestamp_path.write_text(last_modified or "")
        return pd.read_csv(csv_path), last_modified

    return pd.read_csv(csv_path), cached_last_modified
