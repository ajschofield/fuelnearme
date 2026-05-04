import argparse
import math
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from fnme.constants import SORT_KV


def process_stations(
    dframe: pd.DataFrame, arguments: argparse.Namespace, loc: Tuple[float, float]
) -> List[Dict[str, Any]]:

    def bounding_box() -> pd.DataFrame:
        lat, lon = loc
        deg_lat = arguments.radius / 69.0
        deg_lon = arguments.radius / (69.0 * math.cos(math.radians(lat)))
        return dframe[
            dframe["forecourts.location.latitude"].between(lat - deg_lat, lat + deg_lat)
            & dframe["forecourts.location.longitude"].between(
                lon - deg_lon, lon + deg_lon
            )
        ]

    def haversine_miles(lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
        R = 3958.8
        lat1, lon1 = np.radians(loc[0]), np.radians(loc[1])
        lat2, lon2 = np.radians(lat2), np.radians(lon2)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        return R * 2 * np.arcsin(np.sqrt(a))

    def pence_to_pounds(col: pd.Series) -> pd.Series:
        return (col / 100).round(2).where(col.notna(), other="N/A")

    df = bounding_box().copy()

    df["distance"] = haversine_miles(
        df["forecourts.location.latitude"].to_numpy(),
        df["forecourts.location.longitude"].to_numpy(),
    ).round(1)

    df = df[df["distance"] < arguments.radius]

    df = df.assign(
        e5_price=pence_to_pounds(df["forecourts.fuel_price.E5"]),
        e10_price=pence_to_pounds(df["forecourts.fuel_price.E10"]),
        diesel_price=pence_to_pounds(df["forecourts.fuel_price.B7S"]),
    )

    return df.rename(columns={"forecourts.trading_name": "station_name"})[
        ["station_name", "distance", "e5_price", "e10_price", "diesel_price"]
    ].to_dict(orient="records")


def sort_stations(stations: list[dict], sort: str) -> list[dict]:
    sort_key = SORT_KV[sort]
    return sorted(stations, key=lambda d: d[sort_key] if d[sort_key] != "N/A" else 999)
