import argparse
import sys

from constants import SORT_KV
from helpers import (
    filter_df,
    get_latest_data,
    get_location,
    output_stations,
    sort_stations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address", type=str, required=True)
    parser.add_argument("-r", "--radius", type=int, default=5)
    parser.add_argument("-s", "--sort", type=str, default="e10", choices=SORT_KV.keys())
    return parser.parse_args()


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
