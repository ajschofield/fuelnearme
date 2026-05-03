from io import StringIO
from typing import Optional

import pandas as pd
import requests
from constants import ENDPOINT, HEADERS


def get_latest_data() -> tuple[pd.DataFrame, Optional[str]]:
    response = requests.get(ENDPOINT, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text)), response.headers.get("Last-Modified")
