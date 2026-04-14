import argparse
import sys
from io import StringIO
from textwrap import dedent

import pandas as pd
import requests
from colorama import Back, Fore, Style, just_fix_windows_console
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

just_fix_windows_console()


ENDPOINT = "https://www.fuel-finder.service.gov.uk/internal/v1.0.2/csv/get-latest-fuel-prices-csv"
near_stations = []


def get_location(address):
    loc = Nominatim(user_agent="FuelNearMe")
    getLoc = loc.geocode(address)
    if not getLoc:
        print("[*] Failed to get location. Please check if the address is valid.")
        sys.exit(1)
    latitude = getLoc.latitude
    longitude = getLoc.longitude
    return (latitude, longitude)


def get_latest_data():
    response = requests.get(ENDPOINT)
    return pd.read_csv(StringIO(response.text)), response.headers.get("Last-Modified")


parser = argparse.ArgumentParser()
parser.add_argument("-a", "--address", type=str, required=True)
parser.add_argument("-r", "--radius", type=int, default=5)
parser.add_argument("-s", "--sort", type=str, default="e10")
args = parser.parse_args()

location = get_location(args.address)

df, last_modified = get_latest_data()

print(f"Last modified: {last_modified}")

price_cols = [c for c in df.columns if "fuel_price" in c]
df[price_cols] = df[price_cols].fillna(0.0)
df = df.fillna("N/A")

print(f"\n{Fore.MAGENTA}Stations: " + Style.RESET_ALL + str(len(df)))

for station, latitude, longitude, e5_price, e10_price, diesel_price in zip(
    df["forecourts.trading_name"],
    df["forecourts.location.latitude"],
    df["forecourts.location.longitude"],
    df["forecourts.fuel_price.E5"],
    df["forecourts.fuel_price.E10"],
    df["forecourts.fuel_price.B7S"],
):
    distance_from_current_location = geodesic((latitude, longitude), location).miles
    if distance_from_current_location < args.radius:
        station_dict = {
            "station_name": station,
            "distance": round(distance_from_current_location, 1),
            "e5_price": round(e5_price / 100, 2),
            "e10_price": round(e10_price / 100, 2),
            "diesel_price": round(diesel_price / 100, 2),
        }
        near_stations.append(station_dict)

match args.sort:
    case "e10":
        sort_by = "e10_price"
    case "e5":
        sort_by = "e5_price"
    case "b7s":
        sort_by = "diesel_price"
    case "distance":
        sort_by = "distance"

near_stations_sorted_by_price = sorted(near_stations, key=lambda d: d[sort_by])

for number, row in enumerate(near_stations_sorted_by_price):
    output = dedent(f"""
    {number + 1}. {row["station_name"]}
    Distance: {row["distance"]} miles
    E5 Price: £{row["e5_price"]:.2f}/L
    E10 Price: £{row["e10_price"]:.2f}/L
    B7S (Standard Diesel) Price: £{row["diesel_price"]:.2f}/L""")
    print(output)
