import argparse
import sys
from typing import Any, Dict, List

from tabulate import tabulate

from fnme.constants import SORT_KV
from fnme.data import get_latest_data
from fnme.geo import get_location
from fnme.station import process_stations, sort_stations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address", type=str, required=True)
    parser.add_argument("-r", "--radius", type=int, default=5)
    parser.add_argument("-s", "--sort", type=str, default="e10", choices=SORT_KV.keys())
    return parser.parse_args()


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

    df_filtered = process_stations(df, args, location)

    sorted_stations_list = sort_stations(df_filtered, args.sort)

    output_stations(sorted_stations_list)


if __name__ == "__main__":
    main()
