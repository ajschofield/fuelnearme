import argparse
import sys
from io import StringIO
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from geopy.distance import geodesic
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
    parser.add_argument("-s", "--sort", type=str, default="e10")
    return parser.parse_args()


def get_location(address: str) -> tuple[float, float]:
    geolocator = Nominatim(user_agent="FuelNearMe")
    result = geolocator.geocode(address)
    if not isinstance(result, Location):
        print("[*] Failed to get location. Please check if the address is valid.")
        sys.exit(1)
    return (result.latitude, result.longitude)


def get_latest_data() -> Tuple[pd.DataFrame, Optional[str]]:
    response = requests.get(ENDPOINT, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text)), response.headers.get("Last-Modified")


def process_data(dframe: pd.DataFrame) -> pd.DataFrame:
    price_cols = [c for c in dframe.columns if "fuel_price" in c]
    dframe[price_cols] = dframe[price_cols].fillna(0.0)
    return dframe.fillna("N/A")


def filter_df(
    dframe: pd.DataFrame, arguments: argparse.Namespace, loc: Tuple[float, float]
) -> List[Dict[str, Any]]:
    near_stations = []
    for station, latitude, longitude, e5_price, e10_price, diesel_price in zip(
        dframe["forecourts.trading_name"],
        dframe["forecourts.location.latitude"],
        dframe["forecourts.location.longitude"],
        dframe["forecourts.fuel_price.E5"],
        dframe["forecourts.fuel_price.E10"],
        dframe["forecourts.fuel_price.B7S"],
    ):
        distance_from_current_location = geodesic((latitude, longitude), loc).miles
        if distance_from_current_location < arguments.radius:
            station_dict = {
                "station_name": station,
                "distance": round(distance_from_current_location, 1),
                "e5_price": round(e5_price / 100, 2),
                "e10_price": round(e10_price / 100, 2),
                "diesel_price": round(diesel_price / 100, 2),
            }
            na_dict = {
                k: (v if v != 0.00 else "N/A") for (k, v) in station_dict.items()
            }
            near_stations.append(na_dict)
    return near_stations


def sort_stations(stations: list[dict], sort: str) -> list[dict]:
    sort_key = SORT_KV.get(sort)
    return sorted(stations, key=lambda d: d[sort_key] if d[sort_key] != "N/A" else 999)


def output_stations(stations: List[Dict[str, Any]]) -> None:
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
    location = get_location(args.address)
    df, last_modified = get_latest_data()

    print(f"Last modified: {last_modified}")

    df_processed = process_data(df)

    df_filtered = filter_df(df_processed, args, location)

    sorted_stations_list = sort_stations(df_filtered, args.sort)

    output_stations(sorted_stations_list)


if __name__ == "__main__":
    main()
