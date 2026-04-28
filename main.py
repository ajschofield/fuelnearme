import argparse
import math
import sys
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from geopy.geocoders import Nominatim
from geopy.location import Location
from tabulate import tabulate

ENDPOINT = "https://www.fuel-finder.service.gov.uk/internal/v1.0.2/csv/get-latest-fuel-prices-csv"

SORT_KV = {
    "e10": "e10_price",
    "e5": "e5_price",
    "b7s": "diesel_price",
    "distance": "distance",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/533.45 (KHTML, like Gecko) Chrome/48.0.2094.221 Safari/602"
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address", type=str, required=True)
    parser.add_argument("-r", "--radius", type=int, default=5)
    parser.add_argument("-s", "--sort", type=str, default="e10", choices=SORT_KV.keys())
    return parser.parse_args()


def get_location(address: str) -> tuple[float, float]:
    geolocator = Nominatim(user_agent="FuelNearMe")
    result = geolocator.geocode(address)
    if not isinstance(result, Location):
        raise ValueError(f"Failed to get location from address: '{address}'")
    return (result.latitude, result.longitude)


def get_latest_data() -> tuple[pd.DataFrame, Optional[str]]:
    response = requests.get(ENDPOINT, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text)), response.headers.get("Last-Modified")


def filter_df(
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


def output_stations(stations: List[Dict[str, Any]]) -> None:
    if not stations:
        print("[*] No stations found.")
        return
    print(
        tabulate(
            stations,
            headers={
                "station_name": "Station Name",
                "distance": "Distance (miles)",
                "e5_price": "E5 (£/L)",
                "e10_price": "E10 (£/L)",
                "diesel_price": "B7S (£/L)",
            },
            floatfmt=".2f",
        )
    )


def main():
    args = parse_args()

    try:
        location = get_location(args.address)
    except ValueError as e:
        print(f"[*] {e}")
        sys.exit(1)
    df, last_modified = get_latest_data()

    print(f"Last updated: {last_modified}")

    df_filtered = filter_df(df, args, location)

    sorted_stations_list = sort_stations(df_filtered, args.sort)

    output_stations(sorted_stations_list)


if __name__ == "__main__":
    main()
