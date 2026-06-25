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
from app.metrics import brand_averages, pretty_name, summary_stats

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

_MAX_SEARCH_RESULTS = 20
_MAX_REGIONS = 15


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


def read_secret(name: str) -> str:
    """Return a secret from `{name}_FILE` (a Docker secret) if set, else `{name}`."""
    file_path = os.environ.get(f"{name}_FILE")
    if file_path:
        with open(file_path) as f:
            return f.read().strip()
    return os.environ[name]


@st.cache_resource
def get_engine() -> sql.Engine:
    return sql.create_engine(read_secret("DATABASE_URL"))


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
    st.caption("National averages · arrows show day-on-day change")
    cols = st.columns(len(_FUEL_OVERVIEW))
    for col, (key, label) in zip(cols, _FUEL_OVERVIEW):
        data = averages.get(key)
        if not data:
            col.metric(label, "—")
            continue
        delta = deltas.get(key) if deltas else None
        if delta:
            delta_str = f"{delta:+.1f}p"
            delta_color = "inverse"
        elif delta is not None:
            delta_str = "no change"
            delta_color = "off"
        else:
            delta_str = None
            delta_color = "off"
        col.metric(
            label,
            f"{float(data['avg_pence']):.1f}p",
            delta=delta_str,
            delta_color=delta_color,
            help=f"{data['stations']:,} stations",
        )


def render_metrics(stats: dict, fuel_label: str = "") -> None:
    cheapest = stats["cheapest"]
    cheapest_where = " · ".join(
        part for part in (cheapest.get("trading_name"), cheapest.get("city")) if part
    )
    if fuel_label:
        st.caption(fuel_label)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("National average", f"{stats['mean_pence']:.1f}p")
    c2.metric(
        "Cheapest",
        f"{float(cheapest['price_pence']):.1f}p",
        help=cheapest_where or None,
    )
    c3.metric(
        "Stations",
        f"{stats['count']:,}",
        help="Number of stations reporting prices for this fuel type",
    )
    c4.metric(
        "Cheapest–dearest",
        f"{stats['min_pence']:.1f}–{stats['max_pence']:.1f}p",
        help=(
            f"Gap of {stats['spread_pence']:.1f}p per litre between the cheapest "
            "and dearest station nationally"
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
    grad = (
        "linear-gradient(to right,"
        + ",".join(f"rgb({r},{g},{b})" for r, g, b in _HEATMAP_COLORS)
        + ")"
    )
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin-top:4px;">
          <span style="font-size:12px;">Cheaper</span>
          <div style="width:160px;height:10px;border-radius:5px;background:{grad};">
          </div>
          <span style="font-size:12px;">Pricier</span>
          <span style="font-size:12px;color:gray;">
            · national avg {mean:.1f}p · {len(df):,} stations
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _price_bar_chart(df: pd.DataFrame, cat_col: str, val_col: str) -> alt.Chart:
    """Horizontal bar chart of prices, value printed at each bar's end."""
    df = df.copy()
    df[val_col] = df[val_col].astype(float)
    lo, hi = df[val_col].min(), df[val_col].max()
    pad = max(1.0, (hi - lo) * 0.1)
    x = alt.X(
        f"{val_col}:Q",
        title="Avg price (p/l)",
        scale=alt.Scale(domain=[lo - pad, hi + pad * 3]),
        axis=alt.Axis(format=".0f"),
    )
    y = alt.Y(f"{cat_col}:N", sort="x", title=None, axis=None)
    base = alt.Chart(df).encode(x=x, y=y)
    bars = base.mark_bar(
        color="#e63946", cornerRadiusTopRight=3, cornerRadiusBottomRight=3
    )
    # category label inside the left edge of each bar
    cat_labels = base.mark_text(
        align="left",
        baseline="middle",
        dx=6,
        fontSize=12,
        color="white",
    ).encode(text=alt.Text(f"{cat_col}:N"))
    # price value just past the right edge
    val_labels = base.mark_text(
        align="left",
        baseline="middle",
        dx=4,
        fontSize=12,
    ).encode(
        x=alt.X(f"{val_col}:Q", scale=alt.Scale(domain=[lo - pad, hi + pad * 3])),
        text=alt.Text(f"{val_col}:Q", format=".1f"),
    )
    return (bars + cat_labels + val_labels).properties(height=alt.Step(30))


def render_regions(rows: list[dict], fuel_label: str = "") -> None:
    if not rows:
        return
    st.subheader("Prices by region")
    shown = rows[:_MAX_REGIONS]
    caption = f"{len(shown)} cheapest counties"
    if fuel_label:
        caption += f" · {fuel_label}"
    st.caption(caption)
    df = pd.DataFrame(shown)
    st.altair_chart(
        _price_bar_chart(df, "county", "avg_pence"), use_container_width=True
    )


_MIN_DAYS_TREND = 2
_MIN_DAYS_BEST = 14


def render_trend(rows: list[dict]) -> None:
    st.subheader("Price trend")
    st.caption("Daily national average")
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
            x=alt.X(
                "day:T",
                title=None,
                axis=alt.Axis(format="%d %b", tickCount={"interval": "day", "step": 1}),
            ),
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


def render_best_days(data: dict, fuel_label: str = "") -> None:
    st.subheader("Best days to buy")
    caption = "How prices typically vary by day of the week"
    if fuel_label:
        caption += f" · {fuel_label}"
    st.caption(caption)
    days_available = data.get("days_available", 0)
    if days_available < _MIN_DAYS_BEST:
        remaining = _MIN_DAYS_BEST - days_available
        st.caption(
            f"Check back in {remaining} more day{'s' if remaining != 1 else ''} "
            "— not enough history yet."
        )
        return
    rows = data.get("rows", [])
    if not rows:
        return
    df = pd.DataFrame(rows)
    df["avg_pence"] = df["avg_pence"].astype(float)
    best = df.loc[df["avg_pence"].idxmin(), "day_name"]
    st.caption(f"Historically cheapest day: **{best}**")
    st.altair_chart(
        _price_bar_chart(df, "day_name", "avg_pence"), use_container_width=True
    )


def render_brands(prices: list[dict]) -> None:
    rows = brand_averages(prices)
    if len(rows) < 2:
        return
    df = pd.DataFrame(rows)
    st.subheader("Average price by brand")
    st.caption("Brands with 10+ stations · cheapest first")
    st.altair_chart(
        _price_bar_chart(df, "brand", "avg_pence"), use_container_width=True
    )


def _geo_allowed() -> bool:
    """Browser geolocation requires HTTPS or localhost."""
    try:
        headers = st.context.headers
        host = headers.get("host", "")
        proto = headers.get("x-forwarded-proto", headers.get("x-scheme", ""))
        return (
            host.startswith("localhost") or host.startswith("127.") or proto == "https"
        )
    except Exception:
        return False


def render_search(engine: sql.Engine, fuel_type: str) -> None:
    st.subheader("Find stations near you", anchor=False)
    st.caption("Enter a postcode or address to find the cheapest stations nearby")

    geo_ok = _geo_allowed()

    input_col, locate_col = st.columns([6, 1], vertical_alignment="bottom")
    with input_col:
        address = st.text_input(
            "Postcode or address",
            placeholder="e.g. LS11 or Leeds city centre",
            label_visibility="collapsed",
        )
    with locate_col:
        # Custom components can't live in st.form, so the form is built manually.
        if geo_ok:
            geo = streamlit_geolocation()
        else:
            geo = None
            st.button(
                "📍",
                disabled=True,
                key="locate_disabled",
                help="Unavailable on an insecure connection — "
                "enter a postcode instead.",
            )

    with st.expander("Search radius"):
        radius = st.slider(
            "Radius (miles)", min_value=1, max_value=20, value=5, key="search_radius"
        )

    submitted = st.button("Search", type="primary", use_container_width=True)

    # Resolve a search origin: geolocation fires on its own; the Search button
    # geocodes the typed address. Persist it so results survive unrelated reruns.
    geo_lat = geo.get("latitude") if geo else None
    geo_lon = geo.get("longitude") if geo else None
    if geo_lat and geo_lon:
        st.session_state["search_origin"] = (float(geo_lat), float(geo_lon))
    elif submitted and address:
        with st.spinner("Locating..."):
            coords = geocode(address)
        if coords is None:
            st.error("Could not find that location. Try a postcode or town name.")
            return
        st.session_state["search_origin"] = coords
    elif submitted:
        st.warning("Enter a postcode or address to search.")
        return

    origin = st.session_state.get("search_origin")
    if not origin:
        return
    lat, lon = origin
    rows = get_nearby_stations(
        engine, lat, lon, radius_miles=radius, fuel_type=fuel_type
    )

    if not rows:
        st.warning(
            f"No {_FUEL_LABELS[fuel_type]} stations found within {radius} miles."
        )
        return

    rows = sorted(rows, key=lambda r: float(r["price_pence"]))[:_MAX_SEARCH_RESULTS]
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
        r["price"] = float(r["price_pence"])

    st.caption(
        f"{len(rows)} cheapest **{_FUEL_LABELS[fuel_type]}** "
        f"station{'s' if len(rows) != 1 else ''} within {radius} miles · "
        "cheapest first"
    )

    map_col, list_col = st.columns([2, 3])
    with map_col:
        _render_search_map(rows, lat, lon)
    with list_col:
        for r in rows:
            _render_station_card(r)


def _render_search_map(rows: list[dict], lat: float, lon: float) -> None:
    df = pd.DataFrame(rows)
    p_mean = df["price"].mean()
    p_std = df["price"].std() or 1.0
    df["color"] = df["price"].apply(lambda p: price_colour(p, p_mean, p_std))
    df["rank_label"] = df["rank"].astype(str)
    df["price_label"] = df["price"].apply(lambda p: f"{p:.1f}p")

    pins = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=320,
        pickable=True,
    )
    labels = pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["longitude", "latitude"],
        get_text="rank_label",
        get_size=14,
        get_color=[255, 255, 255],
        get_alignment_baseline="'center'",
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[pins, labels],
            initial_view_state=pdk.ViewState(
                latitude=lat, longitude=lon, zoom=11, pitch=0
            ),
            tooltip={"text": "#{rank_label} {trading_name}\n{price_label}"},
            map_style=_MAP_STYLE,
        )
    )


def _render_station_card(r: dict) -> None:
    name = pretty_name(r["trading_name"])
    brand = pretty_name(r.get("brand_name"))
    tags = []
    if r.get("is_motorway_service_station"):
        tags.append("🛣️ Motorway")
    if r.get("is_supermarket_service_station"):
        tags.append("🛒 Supermarket")
    meta = f"{r['distance_miles']:.1f} mi · {r.get('postcode') or ''}".strip(" ·")
    if brand and brand.lower() not in name.lower():
        meta = f"{brand} · {meta}"
    maps_url = (
        "https://www.google.com/maps/dir/?api=1&destination="
        f"{r['latitude']},{r['longitude']}"
    )
    with st.container(border=True):
        info_col, price_col = st.columns([3, 1])
        with info_col:
            badge = "🏆 " if r["rank"] == 1 else f"{r['rank']}. "
            st.markdown(f"**{badge}{name}**")
            st.caption(meta + ("  ·  " + " · ".join(tags) if tags else ""))
            st.markdown(f"[Directions →]({maps_url})")
        with price_col:
            st.markdown(f"### {r['price']:.1f}p")


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
        st.warning("No prices yet — data should appear within 30 minutes.")
        prices = []

    stats = summary_stats(prices)
    if stats:
        render_metrics(stats, fuel_label=_FUEL_LABELS[fuel_type])

    if prices:
        col_brands, col_regions = st.columns([3, 2])
        with col_brands:
            render_brands(prices)
        with col_regions:
            try:
                region_rows = get_all_regions(engine, fuel_type=fuel_type)
            except Exception:
                region_rows = []
            render_regions(region_rows, fuel_label=_FUEL_LABELS[fuel_type])


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
        st.warning("No prices yet — data should appear within 30 minutes.")
        prices = []

    view_mode = (
        st.segmented_control(
            "Map style",
            options=["Heatmap", "Points"],
            default="Heatmap",
        )
        or "Heatmap"
    )
    render_map(prices, view_mode)


def _page_trends() -> None:
    engine = get_engine()
    fuel_type = _fuel_selector()

    try:
        trend = get_price_trend(engine, fuel_type=fuel_type)
    except Exception:
        trend = []
    try:
        best_days_data = get_best_days(engine, fuel_type=fuel_type)
    except Exception:
        best_days_data = {"rows": [], "days_available": 0}

    fuel_label = _FUEL_LABELS[fuel_type]
    col_trend, col_best = st.columns([3, 2])
    with col_trend:
        render_trend(trend)
    with col_best:
        render_best_days(best_days_data, fuel_label=fuel_label)


def main() -> None:
    st.set_page_config(page_title="FuelNearMe", page_icon="⛽", layout="wide")
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)

    pg = st.navigation(
        [
            st.Page(_page_overview, title="Overview", icon="📊", default=True),
            st.Page(_page_search, title="Search", icon="🔍"),
            st.Page(_page_map, title="Map", icon="🗺️"),
            st.Page(_page_trends, title="Trends", icon="📈"),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
