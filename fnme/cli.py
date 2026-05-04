import argparse
import sys
from typing import Any

from tabulate import tabulate

from fnme.constants import SORT_KV
from fnme.data import get_latest_data
from fnme.geo import get_location
from fnme.station import process_stations, sort_stations

_PRICE_COLS = {
    "e5_price": "E5 (£/L)",
    "e10_price": "E10 (£/L)",
    "diesel_price": "B7S (£/L)",
}

_HEADERS = {
    "station_name": "Station Name",
    "distance": "Distance (mi)",
    **_PRICE_COLS,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address", type=str, required=True)
    parser.add_argument("-r", "--radius", type=int, default=5)
    parser.add_argument(
        "-s", "--sort", type=str, default="e10", choices=SORT_KV.keys()
    )
    return parser.parse_args()


def _fmt_price(v: float | None) -> str:
    return f"{v:.2f}" if v is not None else "N/A"


def output_stations(stations: list[dict[str, Any]]) -> None:
    if not stations:
        print("[*] No stations found.")
        return

    rows = [
        {**s, **{col: _fmt_price(s[col]) for col in _PRICE_COLS}}
        for s in stations
    ]

    print(tabulate(rows, headers=_HEADERS, floatfmt="1.f"))


def main():
    args = parse_args()

    try:
        location = get_location(args.address)
    except ValueError as e:
        print(f"[*] {e}")
        sys.exit(1)
    df, last_modified = get_latest_data()

    print(f"Last updated: {last_modified}")

    df_filtered = process_stations(df, args.radius, location)

    sorted_stations_list = sort_stations(df_filtered, args.sort)

    output_stations(sorted_stations_list)


if __name__ == "__main__":
    main()
