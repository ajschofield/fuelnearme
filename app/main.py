import os
from datetime import UTC, datetime

import altair as alt
import pandas as pd
import pydeck as pdk
import sqlalchemy as sql
import streamlit as st
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from streamlit_geolocation import streamlit_geolocation

from app.db import (
    get_all_fuel_averages,
    get_best_days,
    get_fuel_deltas,
    get_last_updated,
    get_latest_prices,
    get_nearby_stations,
    get_price_trend,
    get_region_rankings,
)
from app.metrics import brand_averages, summary_stats

st.set_page_config(page_title="FuelNearMe", page_icon="⛽", layout="wide")

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


def _time_ago(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - dt
    mins = int(delta.total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins} min{'s' if mins != 1 else ''} ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours} hr{'s' if hours != 1 else ''} ago"
    return f"{hours // 24}d ago"


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


def render_fuel_overview(averages: dict, deltas: dict | None = None) -> None:
    cols = st.columns(len(_FUEL_OVERVIEW))
    for col, (key, label) in zip(cols, _FUEL_OVERVIEW):
        data = averages.get(key)
        if not data:
            col.metric(label, "—")
            continue
        delta = deltas.get(key) if deltas else None
        delta_str = f"{delta:+.1f}p" if delta is not None else None
        col.metric(
            label,
            f"{float(data['avg_pence']):.1f}p",
            delta=delta_str,
            delta_color="inverse",
            help=f"{data['stations']:,} stations",
        )


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
        p10 = float(df["price_pence"].quantile(0.10))
        p90 = float(df["price_pence"].quantile(0.90))
        layer = pdk.Layer(
            "HexagonLayer",
            data=df,
            get_position=["longitude", "latitude"],
            get_color_weight="price_pence",
            color_aggregation=pdk.types.String("MEAN"),
            color_range=_HEATMAP_COLORS,
            color_domain=[p10, p90],
            radius=12000,
            extruded=False,
            coverage=0.9,
            pickable=True,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={"text": "Mean: {colorValue}p"},
            map_style=_MAP_STYLE,
        )

    st.pydeck_chart(deck)
    st.caption(
        f"Cheaper → green · pricier → red · national average "
        f"{mean:.1f}p · {len(df):,} stations"
    )


def render_regions(rankings: dict) -> None:
    cheapest = rankings.get("cheapest", [])
    dearest = rankings.get("dearest", [])
    if not cheapest and not dearest:
        return

    st.subheader("Regions")
    if cheapest:
        st.markdown("**Cheapest**")
        for r in cheapest:
            st.markdown(
                f"{r['county']} &nbsp; `{float(r['avg_pence']):.1f}p`",
                unsafe_allow_html=True,
            )
    if dearest:
        st.markdown("**Most expensive**")
        for r in dearest:
            st.markdown(
                f"{r['county']} &nbsp; `{float(r['avg_pence']):.1f}p`",
                unsafe_allow_html=True,
            )


_MIN_DAYS_TREND = 2
_MIN_DAYS_BEST = 14


def render_trend(rows: list[dict]) -> None:
    st.subheader("Price trend")
    if len(rows) < _MIN_DAYS_TREND:
        st.info("Collecting history — check back tomorrow for price trend data.")
        return
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["day"])
    df["avg_pence"] = df["avg_pence"].astype(float)
    y_min, y_max = df["avg_pence"].min(), df["avg_pence"].max()
    pad = max(2.0, (y_max - y_min) * 0.15)
    chart = (
        alt.Chart(df)
        .mark_line(color="#e63946", strokeWidth=2)
        .encode(
            x=alt.X("day:T", title=None, axis=alt.Axis(format="%d %b")),
            y=alt.Y(
                "avg_pence:Q",
                title="Price (p)",
                scale=alt.Scale(domain=[y_min - pad, y_max + pad]),
            ),
            tooltip=[
                alt.Tooltip("day:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("avg_pence:Q", title="Avg price (p)", format=".1f"),
            ],
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)


def render_best_days(data: dict) -> None:
    st.subheader("Best days to buy")
    days_available = data.get("days_available", 0)
    if days_available < _MIN_DAYS_BEST:
        remaining = _MIN_DAYS_BEST - days_available
        st.info(
            f"Need {remaining} more day{'s' if remaining != 1 else ''} of data "
            "to identify day-of-week price patterns."
        )
        return
    rows = data.get("rows", [])
    if not rows:
        return
    df = pd.DataFrame(rows)
    df["avg_pence"] = df["avg_pence"].astype(float)
    best = df.loc[df["avg_pence"].idxmin(), "day_name"]
    st.caption(f"Historically cheapest day: **{best}**")
    st.dataframe(
        df[["day_name", "avg_pence"]].rename(
            columns={"day_name": "Day", "avg_pence": "Avg price (p)"}
        ),
        hide_index=True,
        width="stretch",
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
    st.subheader("Find stations near you", anchor=False)

    input_col, geo_col, radius_col = st.columns([3, 1, 1])
    with input_col:
        address = st.text_input(
            "Postcode or address",
            placeholder="e.g. LS11 or Leeds city centre",
            label_visibility="collapsed",
        )
    with geo_col:
        geo = streamlit_geolocation()
    with radius_col:
        radius = st.slider("Radius (miles)", min_value=1, max_value=20, value=5,
                           label_visibility="collapsed")

    # Geolocation takes priority over typed address when available
    geo_lat = geo.get("latitude") if geo else None
    geo_lon = geo.get("longitude") if geo else None
    if geo_lat and geo_lon:
        lat, lon = float(geo_lat), float(geo_lon)
    elif address:
        with st.spinner("Locating..."):
            coords = geocode(address)
        if coords is None:
            st.error("Could not find that location. Try a postcode or town name.")
            return
        lat, lon = coords
    else:
        return
    rows = get_nearby_stations(engine, lat, lon, radius_miles=radius)

    if not rows:
        st.warning(f"No stations found within {radius} miles.")
        return

    df = pd.DataFrame(rows)
    df["price_pence"] = df["price_pence"].astype(float)
    df["price_label"] = df["price_pence"].apply(lambda p: f"{p:.1f}p")
    p_mean = df["price_pence"].mean()
    p_std = df["price_pence"].std() or 1.0
    df["color"] = df["price_pence"].apply(lambda p: price_colour(p, p_mean, p_std))

    map_col, table_col = st.columns([2, 3])

    with map_col:
        local_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df.drop_duplicates("node_id"),
            get_position=["longitude", "latitude"],
            get_fill_color="color",
            get_radius=300,
            pickable=True,
        )
        st.pydeck_chart(pdk.Deck(
            layers=[local_layer],
            initial_view_state=pdk.ViewState(latitude=lat, longitude=lon,
                                              zoom=11, pitch=0),
            tooltip={"text": "{trading_name}\n{price_label}"},
            map_style=_MAP_STYLE,
        ))

    with table_col:
        df_display = df.sort_values(["fuel_type", "price_pence"])
        for fuel in sorted(df_display["fuel_type"].unique()):
            fuel_df = df_display[df_display["fuel_type"] == fuel][
                ["trading_name", "price_pence", "postcode",
                 "is_motorway_service_station", "is_supermarket_service_station"]
            ].rename(columns={
                "trading_name": "Station",
                "price_pence": "Price (p)",
                "postcode": "Postcode",
                "is_motorway_service_station": "Motorway",
                "is_supermarket_service_station": "Supermarket",
            })
            st.markdown(f"**{_FUEL_LABELS.get(fuel, fuel)}**")
            st.dataframe(fuel_df, width="stretch", hide_index=True)


def main() -> None:
    engine = get_engine()

    try:
        last_updated = get_last_updated(engine)
    except Exception:
        last_updated = None

    title_col, badge_col = st.columns([5, 1])
    with title_col:
        st.title("⛽ FuelNearMe")
        st.caption("Live UK fuel prices — find the cheapest forecourt near you.")
    with badge_col:
        if last_updated:
            st.metric("Updated", _time_ago(last_updated))

    try:
        fuel_overview = get_all_fuel_averages(engine)
        fuel_deltas = get_fuel_deltas(engine)
    except Exception:
        fuel_overview = {}
        fuel_deltas = {}
    if fuel_overview:
        render_fuel_overview(fuel_overview, fuel_deltas)
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

    render_search(engine, fuel_type)

    st.divider()

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

    try:
        trend = get_price_trend(engine, fuel_type=fuel_type)
    except Exception:
        trend = []
    render_trend(trend)

    col_left, col_right = st.columns([3, 2])
    with col_left:
        render_brands(prices)
    with col_right:
        try:
            rankings = get_region_rankings(engine, fuel_type=fuel_type)
        except Exception:
            rankings = {}
        render_regions(rankings)

    try:
        best_days_data = get_best_days(engine, fuel_type=fuel_type)
    except Exception:
        best_days_data = {"rows": [], "days_available": 0}
    render_best_days(best_days_data)


if __name__ == "__main__":
    main()
