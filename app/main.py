import os

import pandas as pd
import pydeck as pdk
import sqlalchemy as sql
import streamlit as st
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim

from app.db import get_latest_prices, get_nearby_stations

st.set_page_config(page_title="FuelNearMe", page_icon="⛽", layout="wide")

_FUEL_LABELS = {
    "E10": "E10 (Petrol)",
    "E5": "E5 (Super Petrol)",
    "B7_STANDARD": "B7 Standard (Diesel)",
    "B7_PREMIUM": "B7 Premium (Diesel)",
    "B10": "B10 (Biodiesel)",
    "HVO": "HVO",
}


@st.cache_resource
def get_engine() -> sql.Engine:
    return sql.create_engine(os.environ["DATABASE_URL"])


def geocode(address: str) -> tuple[float, float] | None:
    try:
        geolocator = Nominatim(user_agent="fuelnearme", timeout=10)
        location = geolocator.geocode(f"{address}, UK")
        if location:
            return location.latitude, location.longitude
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None


def price_colour(price: float, lo: float, hi: float) -> list[int]:
    ratio = (price - lo) / (hi - lo) if hi > lo else 0.5
    return [int(255 * ratio), int(255 * (1 - ratio)), 0, 200]


def render_map(prices: list[dict], fuel_label: str) -> None:
    if not prices:
        st.info("No price data available for this fuel type.")
        return

    df = pd.DataFrame(prices)
    lo, hi = float(df["price_pence"].min()), float(df["price_pence"].max())
    df["color"] = df["price_pence"].apply(lambda p: price_colour(float(p), lo, hi))
    df["price_label"] = df["price_pence"].apply(lambda p: f"{float(p)/100:.3f}p/L")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=300,
        pickable=True,
    )

    view = pdk.ViewState(latitude=52.8, longitude=-1.8, zoom=6)
    tooltip = {"text": "{trading_name}\n{price_label}"}

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/light-v10",
    ))
    st.caption(f"Green = cheapest · Red = most expensive · {len(df)} stations shown")


def render_search(engine: sql.Engine, fuel_type: str) -> None:
    st.subheader("Find stations near you")
    col1, col2 = st.columns([3, 1])
    with col1:
        address = st.text_input("Postcode or address", placeholder="e.g. LS11 or Leeds city centre")
    with col2:
        radius = st.slider("Radius (miles)", min_value=1, max_value=20, value=5)

    if not address:
        return

    with st.spinner("Locating..."):
        coords = geocode(address)

    if coords is None:
        st.error("Could not find that location. Try a postcode or town name.")
        return

    lat, lon = coords
    rows = get_nearby_stations(engine, lat, lon, radius_miles=radius)

    if not rows:
        st.warning(f"No stations found within {radius} miles of {address}.")
        return

    df = pd.DataFrame(rows)
    df["price_£"] = (df["price_pence"].astype(float) / 100).round(3)
    df = df.sort_values(["fuel_type", "price_pence"])

    for fuel in sorted(df["fuel_type"].unique()):
        fuel_df = df[df["fuel_type"] == fuel][
            ["trading_name", "price_£", "postcode", "city",
             "is_motorway_service_station", "is_supermarket_service_station"]
        ].rename(columns={
            "trading_name": "Station",
            "price_£": "Price (£/L)",
            "postcode": "Postcode",
            "city": "City",
            "is_motorway_service_station": "Motorway",
            "is_supermarket_service_station": "Supermarket",
        })
        st.markdown(f"**{_FUEL_LABELS.get(fuel, fuel)}**")
        st.dataframe(fuel_df, use_container_width=True, hide_index=True)


def main() -> None:
    st.title("⛽ FuelNearMe")

    with st.sidebar:
        st.header("Map options")
        fuel_type = st.selectbox(
            "Fuel type for map",
            options=list(_FUEL_LABELS.keys()),
            format_func=lambda k: _FUEL_LABELS[k],
        )

    engine = get_engine()

    with st.spinner("Loading prices..."):
        prices = get_latest_prices(engine, fuel_type=fuel_type)

    render_map(prices, _FUEL_LABELS[fuel_type])
    st.divider()
    render_search(engine, fuel_type)


if __name__ == "__main__":
    main()
