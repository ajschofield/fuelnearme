import os

import pandas as pd
import pydeck as pdk
import sqlalchemy as sql
import streamlit as st
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim

from app.db import get_all_fuel_averages, get_latest_prices, get_nearby_stations
from app.metrics import brand_averages, summary_stats

st.set_page_config(page_title="FuelNearMe", page_icon="⛽", layout="centered")

_FUEL_LABELS = {
    "E10": "E10 (Petrol)",
    "E5": "E5 (Super Petrol)",
    "B7_STANDARD": "B7 Standard (Diesel)",
    "B7_PREMIUM": "B7 Premium (Diesel)",
    "B10": "B10 (Biodiesel)",
    "HVO": "HVO",
}

# Green (cheap) -> red (expensive), used for both the heatmap and the points.
_HEATMAP_COLORS = [
    [26, 152, 80],
    [145, 207, 96],
    [217, 239, 139],
    [254, 224, 139],
    [252, 141, 89],
    [215, 48, 39],
]

_MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


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


def price_colour(price: float, mean: float, std: float) -> list[int]:
    # Clamp to ±2 standard deviations from the mean; centre = yellow
    deviation = (price - mean) / (std if std > 0 else 1.0)
    ratio = max(0.0, min(1.0, (deviation + 2.0) / 4.0))
    r = int(255 * ratio)
    g = int(255 * (1.0 - ratio))
    return [r, g, 0, 220]


_FUEL_OVERVIEW = [
    ("E10", "E10"),
    ("E5", "E5 Super"),
    ("B7_STANDARD", "Diesel"),
    ("B7_PREMIUM", "Premium"),
]


def render_fuel_overview(averages: dict) -> None:
    cols = st.columns(len(_FUEL_OVERVIEW))
    for col, (key, label) in zip(cols, _FUEL_OVERVIEW):
        data = averages.get(key)
        if data:
            col.metric(label, f"{float(data['avg_pence']):.1f}p",
                       help=f"{data['stations']:,} stations")
        else:
            col.metric(label, "—")


def render_metrics(stats: dict) -> None:
    cheapest = stats["cheapest"]
    cheapest_where = " · ".join(
        part for part in (cheapest.get("trading_name"), cheapest.get("city")) if part
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("National average", f"{stats['mean_pence']:.1f}p")
    c2.metric(
        "Cheapest",
        f"{float(cheapest['price_pence']):.1f}p",
        help=cheapest_where or None,
    )
    c3.metric("Stations", f"{stats['count']:,}")
    c4.metric(
        "Spread",
        f"{stats['spread_pence']:.1f}p",
        help=f"{stats['min_pence']:.1f}p to {stats['max_pence']:.1f}p across stations",
    )


def render_map(prices: list[dict], view_mode: str = "Heatmap") -> None:
    if not prices:
        st.info("No price data available for this fuel type.")
        return

    df = pd.DataFrame(prices)
    df["price_pence"] = df["price_pence"].astype(float)
    mean = df["price_pence"].mean()
    std = df["price_pence"].std()
    if pd.isna(std) or std == 0:
        std = 1.0

    view = pdk.ViewState(latitude=54.2, longitude=-2.4, zoom=5.1)

    if view_mode == "Points":
        df["color"] = df["price_pence"].apply(lambda p: price_colour(p, mean, std))
        df["price_label"] = df["price_pence"].apply(lambda p: f"{p:.1f}p")
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["longitude", "latitude"],
            get_fill_color="color",
            get_radius=600,
            pickable=True,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={"text": "{trading_name}\n{price_label}"},
            map_style=_MAP_STYLE,
        )
    else:
        layer = pdk.Layer(
            "HeatmapLayer",
            data=df,
            get_position=["longitude", "latitude"],
            get_weight="price_pence",
            aggregation=pdk.types.String("MEAN"),
            color_range=_HEATMAP_COLORS,
            color_domain=[mean - 1.5 * std, mean + 1.5 * std],
            radius_pixels=45,
            opacity=0.75,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            map_style=_MAP_STYLE,
        )

    st.pydeck_chart(deck)
    st.caption(
        f"Cheaper → green · pricier → red · national average "
        f"{mean:.1f}p · {len(df):,} stations"
    )


def render_brands(prices: list[dict]) -> None:
    rows = brand_averages(prices)
    if len(rows) < 2:
        return

    df = pd.DataFrame(rows).rename(
        columns={"brand": "Brand", "avg_pence": "Avg price", "stations": "Stations"}
    )
    lo, hi = df["Avg price"].min(), df["Avg price"].max()

    st.subheader("Average price by brand")
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "Avg price": st.column_config.ProgressColumn(
                "Avg price",
                format="%.1fp",
                min_value=float(lo) - 0.5,
                max_value=float(hi),
            ),
        },
    )


def render_search(engine: sql.Engine, fuel_type: str) -> None:
    st.subheader("Find stations near you")
    col1, col2 = st.columns([3, 1])
    with col1:
        address = st.text_input(
            "Postcode or address",
            placeholder="e.g. LS11 or Leeds city centre",
        )
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
    df["price_pence"] = df["price_pence"].astype(float)
    df["price_£"] = (df["price_pence"] / 100).round(3)
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
        st.dataframe(fuel_df, width="stretch", hide_index=True)


def main() -> None:
    st.title("⛽ FuelNearMe")
    st.caption("Live UK fuel prices — find the cheapest forecourt near you.")

    engine = get_engine()

    try:
        fuel_overview = get_all_fuel_averages(engine)
    except Exception:
        fuel_overview = {}
    if fuel_overview:
        render_fuel_overview(fuel_overview)
        st.divider()

    fuel_type = (
        st.segmented_control(
            "Fuel type",
            options=list(_FUEL_LABELS.keys()),
            format_func=lambda k: _FUEL_LABELS[k],
            default="E10",
            label_visibility="collapsed",
        )
        or "E10"
    )

    try:
        with st.spinner("Loading prices..."):
            prices = get_latest_prices(engine, fuel_type=fuel_type)
    except Exception:
        st.warning("Price data not yet available — the pipeline may still be loading.")
        prices = []

    stats = summary_stats(prices)
    if stats:
        render_metrics(stats)

    view_mode = (
        st.segmented_control(
            "Map view",
            options=["Heatmap", "Points"],
            default="Heatmap",
            label_visibility="collapsed",
        )
        or "Heatmap"
    )
    render_map(prices, view_mode)

    render_brands(prices)
    st.divider()
    render_search(engine, fuel_type)


if __name__ == "__main__":
    main()
