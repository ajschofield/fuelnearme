import argparse
import sys
from io import StringIO
from textwrap import dedent

import pandas as pd
import requests
from colorama import Fore, Style
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.location import Location

ENDPOINT = "https://www.fuel-finder.service.gov.uk/internal/v1.0.2/csv/get-latest-fuel-prices-csv"


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


def get_latest_data():
    response = requests.get(ENDPOINT)
    return pd.read_csv(StringIO(response.text)), response.headers.get("Last-Modified")


def process_data(dframe):
    price_cols = [c for c in dframe.columns if "fuel_price" in c]
    dframe[price_cols] = dframe[price_cols].fillna(0.0)
    return dframe.fillna("N/A")


def filter_df(dframe, arguments, loc):
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
            near_stations.append(station_dict)
    return near_stations


def sort_list_of_stations(stations_list, arguments):
    match arguments.sort:
        case "e10":
            sort_by = "e10_price"
            return sorted(stations_list, key=lambda d: d[sort_by])
        case "e5":
            sort_by = "e5_price"
            return sorted(stations_list, key=lambda d: d[sort_by])
        case "b7s":
            sort_by = "diesel_price"
            return sorted(stations_list, key=lambda d: d[sort_by])
        case "distance":
            sort_by = "distance"
            return sorted(stations_list, key=lambda d: d[sort_by])


def output_stations(stations):
    for number, row in enumerate(stations):
        output = dedent(f"""
        {number + 1}. {row["station_name"]}
        Distance: {row["distance"]} miles
        E5 Price: £{row["e5_price"]:.2f}/L
        E10 Price: £{row["e10_price"]:.2f}/L
        B7S (Standard Diesel) Price: £{row["diesel_price"]:.2f}/L""")
        print(output)


def main():
    args = parse_args()
    location = get_location(args.address)
    df, last_modified = get_latest_data()

    print(f"Last modified: {last_modified}")

    df_processed = process_data(df)

    print(f"\n{Fore.MAGENTA}Stations: " + Style.RESET_ALL + str(len(df_processed)))

    df_filtered = filter_df(df_processed, args, location)

    sorted_stations_list = sort_list_of_stations(df_filtered, args)

    output_stations(sorted_stations_list)


if __name__ == "__main__":
    main()
