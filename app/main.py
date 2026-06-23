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
    get_all_regions,
    get_best_days,
    get_fuel_deltas,
    get_last_updated,
    get_latest_prices,
    get_nearby_stations,
    get_price_trend,
)
from app.metrics import brand_averages, summary_stats

_FUEL_LABELS = {
    "E10": "E10",
    "E5": "E5 Super",
    "B7_STANDARD": "B7 Standard",
    "B7_PREMIUM": "B7 Premium",
    "B10": "B10",
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
    ("E10", _FUEL_LABELS["E10"]),
    ("E5", _FUEL_LABELS["E5"]),
    ("B7_STANDARD", _FUEL_LABELS["B7_STANDARD"]),
    ("B7_PREMIUM", _FUEL_LABELS["B7_PREMIUM"]),
]


def render_fuel_overview(averages: dict, deltas: dict | None = None) -> None:
    st.caption("National average pump price · arrow shows day-on-day change")
    cols = st.columns(len(_FUEL_OVERVIEW))
    for col, (key, label) in zip(cols, _FUEL_OVERVIEW):
        data = averages.get(key)
        if not data:
            col.metric(label, "—")
            continue
        delta = deltas.get(key) if deltas else None
        delta_str = f"{delta:+.1f}p" if delta else None
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
    c3.metric("Stations", f"{stats['count']:,}",
              help="Number of stations reporting prices for this fuel type")
    c4.metric(
        "Spread",
        f"{stats['spread_pence']:.1f}p",
        help=(
            f"Price range per litre: {stats['min_pence']:.1f}p (cheapest) "
            f"to {stats['max_pence']:.1f}p (dearest) across all stations"
        ),
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

    view = pdk.ViewState(latitude=54.5, longitude=-2.8, zoom=5.8)

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


def render_regions(rows: list[dict]) -> None:
    if not rows:
        return
    st.subheader("Prices by region")
    st.caption("Average price per county · click a column header to sort")
    df = pd.DataFrame(rows)
    df["avg_pence"] = df["avg_pence"].astype(float)
    lo, hi = df["avg_pence"].min(), df["avg_pence"].max()
    df = df.rename(columns={
        "county": "County", "avg_pence": "Avg price (p)", "stations": "Stations"
    })
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Avg price (p)": st.column_config.ProgressColumn(
                "Avg price (p)", format="%.1fp",
                min_value=float(lo) - 1, max_value=float(hi),
            ),
        },
    )


_MIN_DAYS_TREND = 2
_MIN_DAYS_BEST = 14


def render_trend(rows: list[dict]) -> None:
    st.subheader("Price trend")
    st.caption("Daily national average for the selected fuel type")
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
            x=alt.X("day:T", title=None,
                    axis=alt.Axis(format="%d %b", tickCount=len(df))),
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
    st.caption("Day-of-week price patterns based on historical data")
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
    st.caption("Brands with 10+ stations · cheapest first")
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


def _geo_allowed() -> bool:
    """Browser geolocation requires HTTPS or localhost."""
    try:
        headers = st.context.headers
        host = headers.get("host", "")
        proto = headers.get("x-forwarded-proto", headers.get("x-scheme", ""))
        return (
            host.startswith("localhost")
            or host.startswith("127.")
            or proto == "https"
        )
    except Exception:
        return False


def render_search(engine: sql.Engine, fuel_type: str) -> None:
    st.subheader("Find stations near you", anchor=False)
    st.caption("Enter a postcode or address to find the cheapest stations nearby")

    geo_ok = _geo_allowed()

    with st.form("search_form"):
        if geo_ok:
            input_col, geo_col, radius_col, btn_col = st.columns([3, 1, 1, 1])
        else:
            input_col, radius_col, btn_col = st.columns([4, 1, 1])

        with input_col:
            address = st.text_input(
                "Postcode or address",
                placeholder="e.g. LS11 or Leeds city centre",
                label_visibility="collapsed",
            )

        if geo_ok:
            with geo_col:
                geo = streamlit_geolocation()
        else:
            geo = None

        with radius_col:
            radius = st.slider("Radius (miles)", min_value=1, max_value=20, value=5)

        with btn_col:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            submitted = st.form_submit_button("Search", use_container_width=True)

    if not geo_ok:
        st.caption(
            "⚠️ Geolocation requires HTTPS — enter a postcode above instead.",
            help="Browsers block geolocation on plain HTTP. "
                 "Access via https:// or localhost to enable the 'Near me' button.",
        )

    if not submitted and not (geo and geo.get("latitude")):
        return

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
            lo = float(fuel_df["Price (p)"].min())
            hi = float(fuel_df["Price (p)"].max())
            st.markdown(f"**{_FUEL_LABELS.get(fuel, fuel)}**")
            st.dataframe(
                fuel_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Price (p)": st.column_config.ProgressColumn(
                        "Price (p)", format="%.1fp",
                        min_value=lo - 1, max_value=hi,
                    ),
                },
            )


_LIGHT_OVERRIDES = """
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #f8f9fa !important;
    }
    [data-testid="stHeader"] {
        background-color: #f8f9fa !important;
        border-bottom: 1px solid #dee2e6 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #dee2e6 !important;
    }
    [data-testid="stSidebarNav"] a span,
    [data-testid="stSidebarNavItems"] a span {
        color: #212529 !important;
    }
    .stMarkdown p, .stMarkdown li, .stMarkdown span,
    [data-testid="stCaptionContainer"] p,
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricValue"],
    [data-testid="stText"],
    label, .stSelectbox label, .stSlider label,
    h1, h2, h3, h4, h5 {
        color: #212529 !important;
    }
    [data-testid="stMetricDeltaIcon"], [data-testid="stMetricDelta"] {
        color: inherit !important;
    }
    .stAlert, [data-testid="stInfo"] {
        background-color: #e3f2fd !important;
        color: #0c4a6e !important;
    }
    [data-testid="stDataFrameContainer"] > div {
        background-color: #ffffff !important;
    }
    input, textarea {
        background-color: #ffffff !important;
        color: #212529 !important;
        border-color: #ced4da !important;
    }
    [data-testid="stSegmentedControl"] button {
        color: #212529 !important;
    }
"""

_AUTO_THEME = (
    f"<style>@media (prefers-color-scheme: light) {{ {_LIGHT_OVERRIDES} }}</style>"
)
_THEME_CSS = {
    "Auto": _AUTO_THEME,
    "Light": f"<style>{_LIGHT_OVERRIDES}</style>",
    "Dark": "",
}

_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], button, input, textarea, select {
    font-family: 'Inter', sans-serif !important;
}

@media (max-width: 768px) {
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        width: 100% !important;
        flex: none !important;
        min-width: 100% !important;
    }
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
}
</style>
"""


def _header(engine: sql.Engine) -> None:
    """Title + last-updated badge, shared across all pages."""
    try:
        last_updated = get_last_updated(engine)
    except Exception:
        last_updated = None
    title_col, badge_col = st.columns([4, 2])
    with title_col:
        st.title("⛽ FuelNearMe")
        st.caption("Live UK fuel prices — find the cheapest forecourt near you.")
    with badge_col:
        if last_updated:
            st.metric("Updated", _time_ago(last_updated))


def _fuel_selector() -> str:
    return (
        st.segmented_control(
            "Fuel type",
            options=list(_FUEL_LABELS.keys()),
            format_func=lambda k: _FUEL_LABELS[k],
            default="E10",
            key="fuel_type",
        )
        or "E10"
    )


def _page_overview() -> None:
    engine = get_engine()
    _header(engine)

    try:
        fuel_overview = get_all_fuel_averages(engine)
        fuel_deltas = get_fuel_deltas(engine)
    except Exception:
        fuel_overview = {}
        fuel_deltas = {}
    if fuel_overview:
        render_fuel_overview(fuel_overview, fuel_deltas)
        st.divider()

    fuel_type = _fuel_selector()

    try:
        with st.spinner("Loading prices..."):
            prices = get_latest_prices(engine, fuel_type=fuel_type)
    except Exception:
        st.warning("Price data not yet available — the pipeline may still be loading.")
        prices = []

    stats = summary_stats(prices)
    if stats:
        render_metrics(stats)
    if prices:
        render_brands(prices)


def _page_search() -> None:
    engine = get_engine()
    fuel_type = _fuel_selector()
    render_search(engine, fuel_type)


def _page_map() -> None:
    engine = get_engine()
    fuel_type = _fuel_selector()

    try:
        with st.spinner("Loading prices..."):
            prices = get_latest_prices(engine, fuel_type=fuel_type)
    except Exception:
        st.warning("Price data not yet available — the pipeline may still be loading.")
        prices = []

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


def _page_trends() -> None:
    engine = get_engine()
    fuel_type = _fuel_selector()

    try:
        with st.spinner("Loading prices..."):
            prices = get_latest_prices(engine, fuel_type=fuel_type)
    except Exception:
        st.warning("Price data not yet available — the pipeline may still be loading.")
        prices = []

    try:
        trend = get_price_trend(engine, fuel_type=fuel_type)
    except Exception:
        trend = []
    try:
        best_days_data = get_best_days(engine, fuel_type=fuel_type)
    except Exception:
        best_days_data = {"rows": [], "days_available": 0}

    col_trend, col_best = st.columns([3, 2])
    with col_trend:
        render_trend(trend)
    with col_best:
        render_best_days(best_days_data)

    col_left, col_right = st.columns([3, 2])
    with col_left:
        render_brands(prices)
    with col_right:
        try:
            region_rows = get_all_regions(engine, fuel_type=fuel_type)
        except Exception:
            region_rows = []
        render_regions(region_rows)


def main() -> None:
    st.set_page_config(page_title="FuelNearMe", page_icon="⛽", layout="wide")
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)

    with st.sidebar:
        theme = st.radio(
            "Theme",
            options=["Auto", "Light", "Dark"],
            index=0,
            horizontal=True,
            help="Auto follows your system setting",
        )
    if css := _THEME_CSS.get(theme, ""):
        st.markdown(css, unsafe_allow_html=True)

    pg = st.navigation([
        st.Page(_page_overview, title="Overview", icon="📊", default=True),
        st.Page(_page_search, title="Search", icon="🔍"),
        st.Page(_page_map, title="Map", icon="🗺️"),
        st.Page(_page_trends, title="Trends", icon="📈"),
    ])
    pg.run()


if __name__ == "__main__":
    main()
