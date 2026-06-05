import streamlit as st
import pandas as pd
import folium
import altair as alt
import streamlit.components.v1 as components
from pathlib import Path

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_title="Australian BESS Dispatch Map",
)

# ---------------- STYLING ----------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Cormorant+Garamond:wght@500;600;700&display=swap');

    :root {
        --bg-deep: #421815;
        --bg-mid: #55201b;
        --card: #662820;
        --card-soft: #743027;
        --accent: #ff6938;
        --accent-soft: #e58a65;
        --cream: #f4d8cf;
        --muted: #d6a095;
        --line: rgba(255, 105, 56, 0.55);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    .stApp {
        background:
            radial-gradient(circle at 22% 16%, rgba(255, 105, 56, 0.12), transparent 26%),
            radial-gradient(circle at 86% 72%, rgba(255, 105, 56, 0.10), transparent 30%),
            linear-gradient(180deg, #421815 0%, #4b1b17 52%, #32100f 100%);
        background-attachment: fixed;
        color: var(--cream);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1220px;
    }

    /* Main compact title box */
    .hero-wrap {
        text-align: center;
        margin: 0.5rem 0 1rem 0;
    }

    .hero {
        display: inline-block;
        width: auto;
        max-width: 980px;
        padding: 18px 42px 20px 42px;
        border: 1px solid var(--line);
        border-radius: 22px;
        background: rgba(66, 24, 21, 0.72);
        box-shadow: 0 16px 45px rgba(0, 0, 0, 0.28);
    }

    .hero h1 {
        color: var(--cream);
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 700;
        font-size: clamp(2.5rem, 6vw, 5.2rem);
        line-height: 0.92;
        letter-spacing: -0.04em;
        margin: 0;
    }

    .hero .highlight {
        color: var(--accent);
    }

    .subheader-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin: 0 0 1rem 0;
        color: var(--muted);
        font-size: 0.9rem;
    }

    .subheader-bar a {
        color: var(--accent);
        text-decoration: none;
        font-weight: 600;
    }

    /* Top charging/discharging summary box */
    .status-panel {
        border: 1px solid var(--line);
        background: rgba(84, 32, 27, 0.78);
        border-radius: 20px;
        padding: 18px;
        margin: 16px 0 22px 0;
        box-shadow: 0 16px 38px rgba(0, 0, 0, 0.24);
    }

    .status-title {
        font-family: 'Cormorant Garamond', serif !important;
        color: var(--cream);
        font-size: 2rem;
        line-height: 1;
        margin-bottom: 14px;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
    }

    .metric-card {
        background: rgba(108, 43, 35, 0.92);
        border: 1px solid rgba(255, 105, 56, 0.22);
        border-radius: 14px;
        padding: 18px 20px;
    }

    .metric-label {
        color: var(--cream);
        opacity: 0.9;
        font-size: 1rem;
        margin-bottom: 8px;
    }

    .metric-subtle {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 500;
        margin-left: 6px;
        white-space: nowrap;
    }

    .metric-value {
        color: var(--accent);
        font-size: clamp(2.1rem, 4vw, 3.4rem);
        font-weight: 700;
        line-height: 1;
        letter-spacing: -0.04em;
    }

    .content-card {
        background: rgba(99, 39, 32, 0.86) !important;
        border: 1px solid rgba(255, 105, 56, 0.35);
        padding: 18px;
        border-radius: 18px;
        box-shadow: 0 15px 38px rgba(0, 0, 0, 0.22);
        margin-bottom: 20px;
        color: var(--cream) !important;
        overflow-x: auto;
    }

    .section-title {
        color: var(--cream);
        font-family: 'Cormorant Garamond', serif !important;
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1;
        margin: 22px 0 8px 0;
    }

    .section-title .highlight {
        color: var(--accent);
    }

    .selector-help {
        color: var(--muted);
        font-size: 0.95rem;
        margin: 0 0 8px 0;
    }

    /* Streamlit widgets */
    label, .stSelectbox label, .stMarkdown, p, span, div {
        font-family: 'Inter', sans-serif !important;
    }

    div[data-baseweb="select"] > div {
        background-color: rgba(108, 43, 35, 0.94) !important;
        border: 1px solid rgba(255, 105, 56, 0.45) !important;
        border-radius: 12px !important;
        color: var(--cream) !important;
    }

    div[data-baseweb="select"] span {
        color: var(--cream) !important;
    }

    /* Tables */
    .custom-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin-top: 10px;
        overflow: hidden;
        border-radius: 12px;
        font-size: 0.94rem;
    }

    .custom-table th {
        text-align: left;
        padding: 13px 10px;
        background-color: rgba(255, 105, 56, 0.18);
        color: var(--cream);
        border-bottom: 1px solid rgba(255, 105, 56, 0.28);
        white-space: nowrap;
    }

    .custom-table td {
        padding: 13px 10px;
        border-bottom: 1px solid rgba(255, 105, 56, 0.14);
        color: var(--cream);
        white-space: nowrap;
    }

    .stDataFrame {
        border: 1px solid rgba(255, 105, 56, 0.25);
        border-radius: 15px;
        overflow: hidden;
    }

    /* Map container and warm colour filter for the basemap */
    iframe {
        border-radius: 18px !important;
    }

    .st-key-bess_map, div[data-testid="stIFrame"] {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(255, 105, 56, 0.45);
        box-shadow: 0 20px 42px rgba(0, 0, 0, 0.28);
    }

    /* This targets Folium/Leaflet map tiles and warms them into the red/orange palette.
       The contrast/saturate settings keep land and sea visibly distinct. */
    .leaflet-tile-pane img {
        filter: sepia(82%) hue-rotate(320deg) saturate(1.8) contrast(1.16) brightness(0.82) !important;
    }

    .bess-div-icon {
    background: transparent !important;
    border: 0 !important;
}
.leaflet-popup-content-wrapper {
        background: #4b1b17 !important;
        color: #f4d8cf !important;
        border: 1px solid rgba(255, 105, 56, 0.55);
        border-radius: 13px !important;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.38) !important;
    }

    .leaflet-popup-content {
        width: auto !important;
        min-width: 285px !important;
        max-width: 520px !important;
        margin: 14px 16px !important;
        line-height: 1.45 !important;
        white-space: nowrap !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
    }

    .leaflet-popup-tip {
        background: #4b1b17 !important;
    }

    @media (max-width: 768px) {
        .metric-grid {
            grid-template-columns: 1fr;
        }
        .subheader-bar {
            flex-direction: column;
            align-items: flex-start;
        }
        .table-wrapper {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        .custom-table {
            min-width: 880px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- DATA LOADING ----------------
# Use the GitHub raw CSV in deployment. Keep the local fallback for quick testing.
DATA_URL = "https://raw.githubusercontent.com/rshaw13/au_bess_map/refs/heads/main/data/latest_bess_data.csv"
HISTORY_URL = "https://raw.githubusercontent.com/rshaw13/au_bess_map/refs/heads/main/data/bess_history_24h.csv"
REGIONAL_MARKET_URL = "https://raw.githubusercontent.com/rshaw13/au_bess_map/refs/heads/main/data/regional_market_history_24h.csv"
LOCAL_DATA_FILE = Path("data/latest_bess_data.csv")
LOCAL_HISTORY_FILE = Path("data/bess_history_24h.csv")
LOCAL_REGIONAL_MARKET_FILE = Path("data/regional_market_history_24h.csv")

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    if LOCAL_DATA_FILE.exists():
        return pd.read_csv(LOCAL_DATA_FILE)

    try:
        return pd.read_csv(DATA_URL)
    except Exception as e:
        st.error(
            "Could not load latest BESS data. Check that data/latest_bess_data.csv exists "
            "in the GitHub repo and that DATA_URL points to the correct repo, branch and file."
        )
        st.code(DATA_URL)
        st.exception(e)
        st.stop()


@st.cache_data(ttl=300)
def load_history() -> pd.DataFrame:
    """Load the rolling 24-hour history file created by update_data.py."""
    if LOCAL_HISTORY_FILE.exists():
        return pd.read_csv(LOCAL_HISTORY_FILE)

    try:
        return pd.read_csv(HISTORY_URL)
    except Exception:
        # History will not exist until update_data.py has run at least twice.
        # Return an empty dataframe rather than breaking the whole app.
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_regional_market_history() -> pd.DataFrame:
    """Load rolling 24-hour state/region price, demand, renewable and battery charging history."""
    if LOCAL_REGIONAL_MARKET_FILE.exists():
        return pd.read_csv(LOCAL_REGIONAL_MARKET_FILE)

    try:
        return pd.read_csv(REGIONAL_MARKET_URL)
    except Exception:
        return pd.DataFrame()


df = load_data()

if df.empty:
    st.error("No BESS data found. Run update_data.py first and check data/latest_bess_data.csv was created.")
    st.stop()

# Defensive column cleanup
for col in ["SIGNED_MW", "ABS_MW", "MAX_DISCHARGE_MW", "MAX_CHARGE_MW", "STORAGE_MWH", "utilisation_pct", "Latitude", "Longitude", "REGION_RRP", "REGION_TOTALDEMAND"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["Latitude", "Longitude"])

# Ensure selector options exist before the map is rendered. The selectbox itself is displayed below the map.
asset_options = sorted(df["asset_label"].dropna().unique())
if not asset_options:
    st.error("No valid BESS asset labels found in latest_bess_data.csv.")
    st.stop()

# Default to Waratah Super Battery where present; otherwise use the first asset alphabetically.
def find_default_asset(options):
    for option in options:
        if "waratah" in str(option).lower() and "super" in str(option).lower():
            return option
    for option in options:
        if "waratah" in str(option).lower():
            return option
    return options[0]

if "selected_bess_asset" not in st.session_state or st.session_state["selected_bess_asset"] not in asset_options:
    st.session_state["selected_bess_asset"] = find_default_asset(asset_options)

selected_label = st.session_state["selected_bess_asset"]

# ---------------- HERO ----------------
st.markdown(
    """
    <div class="hero-wrap">
        <div class="hero">
            <h1><span class="highlight">Australian</span> BESS<br>live dispatch map</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

linkedin_url = "https://www.linkedin.com/in/ryan-shaw13/"
st.markdown(
    f"""
    <div class="subheader-bar">
        <div>An energy project by Ryan Shaw.</div>
        <div>Contact me on <a href="{linkedin_url}" target="_blank">LinkedIn</a></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- TOP SUMMARY BOX ----------------
charging_mw = df.loc[df["SIGNED_MW"] < -1, "ABS_MW"].sum()
discharging_mw = df.loc[df["SIGNED_MW"] > 1, "ABS_MW"].sum()
idle_count = int((df["BESS_STATE"] == "Idle").sum())
total_bess_assets = int(df["asset_label"].nunique())

st.markdown(
    f"""
    <div class="status-panel">
        <div class="status-title"><span style="color: var(--accent);">Current</span> charge / discharge position</div>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total discharging</div>
                <div class="metric-value">{discharging_mw:,.1f} MW</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total charging</div>
                <div class="metric-value">{charging_mw:,.1f} MW</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Idle / near idle assets <span class="metric-subtle">of {total_bess_assets} total BESS assets</span></div>
                <div class="metric-value">{idle_count}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- MAP ----------------
def state_colour(state: str, is_selected: bool = False) -> str:
    if is_selected:
        return "#ff6938"
    if state == "Discharging":
        return "#ff6938"   # orange/red = exporting
    if state == "Charging":
        return "#f4d8cf"   # light cream = importing/charging, still inside palette
    return "#a46a5f"       # muted = idle


def safe_float(value, default=0.0) -> float:
    """Avoid NaN marker radii, which can break the Folium/Leaflet render."""
    try:
        value = float(value)
        if pd.isna(value):
            return default
        return value
    except Exception:
        return default

m = folium.Map(
    location=[-27.5, 134.5],
    zoom_start=4,
    tiles="OpenStreetMap",
    width="100%",
    height="600px",
    prefer_canvas=True,
    control_scale=True,
)

# CSS must be injected into the Folium iframe itself. Streamlit page CSS cannot reliably style Leaflet internals.
map_css = """
<style>
.leaflet-container {
    background: #351411 !important;
    font-family: 'Inter', Arial, sans-serif !important;
}
.leaflet-tile-pane img {
    filter: sepia(88%) hue-rotate(320deg) saturate(1.9) contrast(1.2) brightness(0.78) !important;
}
.leaflet-popup-content-wrapper {
    background: #4b1b17 !important;
    color: #f4d8cf !important;
    border: 1px solid rgba(255, 105, 56, 0.7) !important;
    border-radius: 13px !important;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.38) !important;
}
.leaflet-popup-content {
    width: max-content !important;
    min-width: 300px !important;
    max-width: 560px !important;
    margin: 14px 16px !important;
    line-height: 1.45 !important;
    white-space: nowrap !important;
    font-family: 'Inter', Arial, sans-serif !important;
    font-size: 13px !important;
}
.leaflet-popup-tip {
    background: #4b1b17 !important;
}
</style>
"""
m.get_root().html.add_child(folium.Element(map_css))

def html_escape(value) -> str:
    """Tiny HTML escape helper so popup/tooltip text cannot break Folium JavaScript."""
    import html
    return html.escape(str(value))


def marker_sizes(abs_mw: float, discharge_cap: float) -> tuple[int, int]:
    """Return visible pixel sizes for the active dot and capacity ring.

    These are deliberately bounded. The earlier CircleMarker layer could be hard to see
    or fail silently in some Streamlit/Folium iframe renders. DivIcon markers are plain
    HTML, so they are more reliable on Streamlit Cloud.
    """
    dot = int(max(9, min(34, 8 + abs_mw * 0.055)))
    ring = int(max(dot + 10, min(56, 16 + discharge_cap * 0.045)))
    return dot, ring


marker_count = 0

for _, row in df.iterrows():
    lat = safe_float(row.get("Latitude"), None)
    lon = safe_float(row.get("Longitude"), None)
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        continue

    is_selected = row["asset_label"] == selected_label
    abs_mw = safe_float(row.get("ABS_MW"), 0.0)
    discharge_cap = safe_float(row.get("MAX_DISCHARGE_MW"), 0.0)
    signed_mw = safe_float(row.get("SIGNED_MW"), 0.0)
    charge_cap = safe_float(row.get("MAX_CHARGE_MW"), 0.0)
    storage_mwh = safe_float(row.get("STORAGE_MWH"), 0.0)
    utilisation = safe_float(row.get("utilisation_pct"), 0.0)
    region_rrp = safe_float(row.get("REGION_RRP"), None)
    region_demand = safe_float(row.get("REGION_TOTALDEMAND"), None)
    price_text = "n/a" if region_rrp is None or pd.isna(region_rrp) else f"${region_rrp:,.2f}/MWh"
    demand_text = "n/a" if region_demand is None or pd.isna(region_demand) else f"{region_demand:,.0f} MW"
    state = str(row.get("BESS_STATE", "Idle"))

    dot_size, ring_size = marker_sizes(abs_mw, discharge_cap)
    dot_colour = state_colour(state, is_selected)
    ring_colour = "#ff6938" if is_selected else "#d0573c"
    glow = "0 0 0 4px rgba(255,105,56,0.20), 0 0 22px rgba(255,105,56,0.55)" if is_selected else "0 0 14px rgba(255,105,56,0.25)"

    popup_html = f"""
    <div class="bess-popup">
        <div style="font-size:15px; font-weight:800; color:#ff6938; margin-bottom:7px;">{html_escape(row['Station Name'])}</div>
        <div><b>DUID:</b> {html_escape(row['DUID'])}</div>
        <div><b>Region:</b> {html_escape(row['Region'])}</div>
        <div><b>Regional price:</b> {html_escape(price_text)}</div>
        <div><b>Regional demand:</b> {html_escape(demand_text)}</div>
        <div><b>State:</b> {html_escape(state)}</div>
        <div><b>Signed dispatch:</b> {signed_mw:.1f} MW</div>
        <div><b>Discharge capacity:</b> {discharge_cap:.1f} MW</div>
        <div><b>Charge capacity:</b> {charge_cap:.1f} MW</div>
        <div><b>Storage:</b> {storage_mwh:.1f} MWh</div>
        <div><b>Utilisation:</b> {utilisation:.1f}%</div>
    </div>
    """
    popup = folium.Popup(popup_html, max_width=620)

    # Reliable visible marker: an HTML ring sized by capacity with a central dot sized by current MW.
    marker_html = f"""
    <div style="
        width:{ring_size}px;
        height:{ring_size}px;
        border:2px solid {ring_colour};
        border-radius:50%;
        background:rgba(255,105,56,0.08);
        box-shadow:{glow};
        display:flex;
        align-items:center;
        justify-content:center;
        box-sizing:border-box;
    ">
        <div style="
            width:{dot_size}px;
            height:{dot_size}px;
            border-radius:50%;
            background:{dot_colour};
            opacity:0.94;
            border:1px solid rgba(244,216,207,0.65);
            box-sizing:border-box;
        "></div>
    </div>
    """

    folium.Marker(
        location=[lat, lon],
        tooltip=html_escape(row["asset_label"]),
        popup=popup,
        icon=folium.DivIcon(
            html=marker_html,
            icon_size=(ring_size, ring_size),
            icon_anchor=(ring_size // 2, ring_size // 2),
            class_name="bess-div-icon",
        ),
        z_index_offset=1000 if is_selected else 0,
    ).add_to(m)

    marker_count += 1

# Keep Australia in view and avoid a blank-looking map if all assets are clustered.
try:
    bounds = df[["Latitude", "Longitude"]].dropna().values.tolist()
    if bounds:
        m.fit_bounds(bounds, padding=(30, 30))
except Exception:
    pass

# Render Folium directly as HTML instead of using st_folium.
# This avoids a common Streamlit Cloud issue where the Leaflet map iframe mounts
# but stays blank.
if marker_count == 0:
    st.warning("No BESS markers were created. Check Latitude/Longitude columns in data/latest_bess_data.csv.")

map_height = 450 if st.session_state.get("is_mobile", False) else 600
components.html(
    m.get_root().render(),
    height=map_height + 20,
    scrolling=False,
)

st.caption(
    f"Last update (Aus Time): {df['SETTLEMENTDATE'].iloc[0]} — latest public AEMO Dispatch_SCADA data can lag real time. "
    "Positive MW = discharging/exporting; negative MW = charging/importing."
)

# ---------------- SELECTOR BELOW MAP ----------------
st.markdown(
    """
    <div class="section-title"><span class="highlight">Select</span> a BESS asset</div>
    <p class="selector-help">Hover over a battery on the map to find its name, then use the drop-down to view dispatch details in the summary table below.</p>
    """,
    unsafe_allow_html=True,
)

st.selectbox(
    "Select a BESS asset",
    asset_options,
    key="selected_bess_asset",
    label_visibility="collapsed",
)

selected_label = st.session_state["selected_bess_asset"]
selected_row = df[df["asset_label"] == selected_label].iloc[0]

# ---------------- SELECTED ASSET TABLE ----------------
table_df = pd.DataFrame([{
    "BESS Asset": str(selected_row["Station Name"]),
    "DUID": str(selected_row["DUID"]),
    "Region": str(selected_row["Region"]),
    "State": str(selected_row["BESS_STATE"]),
    "Signed Dispatch (MW)": float(round(selected_row["SIGNED_MW"], 1)),
    "Regional Price ($/MWh)": None if pd.isna(selected_row.get("REGION_RRP", pd.NA)) else float(round(selected_row["REGION_RRP"], 2)),
    "Regional Demand (MW)": None if pd.isna(selected_row.get("REGION_TOTALDEMAND", pd.NA)) else float(round(selected_row["REGION_TOTALDEMAND"], 0)),
    "Discharge Capacity (MW)": float(round(selected_row["MAX_DISCHARGE_MW"], 1)),
    "Charge Capacity (MW)": float(round(selected_row["MAX_CHARGE_MW"], 1)),
    "Storage Capacity (MWh)": float(round(selected_row["STORAGE_MWH"], 1)),
    "Utilisation (%)": float(round(selected_row["utilisation_pct"], 0)),
    "Last Update (Aus Time)": str(selected_row["SETTLEMENTDATE"]),
}]).astype(object)

table_html = table_df.to_html(index=False, classes="custom-table")

st.markdown(
    f"""
    <div class="content-card">
        <div class="section-title" style="margin-top: 0; font-size: 1.9rem;"><span class="highlight">Selected</span> BESS asset details</div>
        <div class="table-wrapper">
            {table_html}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- SELECTED ASSET 24H CHART ----------------
history_df = load_history()

st.markdown(
    """
    <div class="section-title"><span class="highlight">Last 24 hours</span> selected asset output</div>
    """,
    unsafe_allow_html=True,
)

if history_df.empty:
    st.info("No 24-hour history file found yet. Run update_data.py on a schedule and the chart will populate as snapshots are cached.")
else:
    # Clean and filter history for the currently selected DUID.
    history_df["SETTLEMENTDATE"] = pd.to_datetime(history_df["SETTLEMENTDATE"], errors="coerce")
    history_df["SIGNED_MW"] = pd.to_numeric(history_df["SIGNED_MW"], errors="coerce")
    history_df = history_df.dropna(subset=["SETTLEMENTDATE", "SIGNED_MW", "DUID"])

    selected_duid = str(selected_row["DUID"])
    asset_history = history_df[history_df["DUID"].astype(str) == selected_duid].copy()
    asset_history = asset_history.sort_values("SETTLEMENTDATE")

    if asset_history.empty:
        st.info("No cached history found for this selected asset yet. The chart will appear after update_data.py has captured a few snapshots.")
    else:
        newest_time = asset_history["SETTLEMENTDATE"].max()
        cutoff = newest_time - pd.Timedelta(hours=24)
        asset_history = asset_history[asset_history["SETTLEMENTDATE"] >= cutoff].copy()
        asset_history["Output MW"] = asset_history["SIGNED_MW"].round(2)
        asset_history["Time"] = asset_history["SETTLEMENTDATE"]
        asset_history["Mode"] = asset_history["Output MW"].apply(
            lambda x: "Discharging" if x > 1 else "Charging" if x < -1 else "Idle"
        )

        y_min = min(float(asset_history["Output MW"].min()), 0.0)
        y_max = max(float(asset_history["Output MW"].max()), 0.0)
        pad = max((y_max - y_min) * 0.12, 5.0)

        line = alt.Chart(asset_history).mark_line(
            color="#ff6938",
            strokeWidth=3,
            interpolate="monotone",
        ).encode(
            x=alt.X("Time:T", title="Time", axis=alt.Axis(labelColor="#d6a095", titleColor="#f4d8cf", gridColor="rgba(255,105,56,0.12)")),
            y=alt.Y("Output MW:Q", title="Signed output MW", scale=alt.Scale(domain=[y_min - pad, y_max + pad]), axis=alt.Axis(labelColor="#d6a095", titleColor="#f4d8cf", gridColor="rgba(255,105,56,0.16)")),
            tooltip=[
                alt.Tooltip("Time:T", title="Time"),
                alt.Tooltip("Output MW:Q", title="Signed output MW", format=",.1f"),
                alt.Tooltip("Mode:N", title="Mode"),
            ],
        )

        points = alt.Chart(asset_history).mark_circle(
            color="#f4d8cf",
            size=48,
            opacity=0.85,
        ).encode(
            x="Time:T",
            y="Output MW:Q",
            tooltip=[
                alt.Tooltip("Time:T", title="Time"),
                alt.Tooltip("Output MW:Q", title="Signed output MW", format=",.1f"),
                alt.Tooltip("Mode:N", title="Mode"),
            ],
        )

        zero_rule = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            color="#d6a095",
            opacity=0.55,
            strokeDash=[5, 5],
        ).encode(y="y:Q")

        chart = (zero_rule + line + points).properties(
            height=330,
            background="rgba(99, 39, 32, 0.86)",
            title={
                "text": f"{selected_row['Station Name']} — signed BESS output",
                "subtitle": "Positive MW = discharging/exporting. Negative MW = charging/importing.",
                "color": "#f4d8cf",
                "subtitleColor": "#d6a095",
                "font": "Inter",
                "fontSize": 18,
                "anchor": "start",
            },
        ).configure_view(
            stroke="rgba(255,105,56,0.35)"
        ).configure_axis(
            labelFont="Inter",
            titleFont="Inter",
            domainColor="rgba(255,105,56,0.30)",
            tickColor="rgba(255,105,56,0.30)",
        )

        st.altair_chart(chart, use_container_width=True)

# ---------------- REGIONAL 24H RENEWABLE/DEMAND VS BATTERY CHARGING CHART ----------------
regional_history_df = load_regional_market_history()

st.markdown(
    """
    <div class="section-title"><span class="highlight">Renewables vs demand</span> and battery charging</div>
    """,
    unsafe_allow_html=True,
)

if regional_history_df.empty:
    st.info(
        "No regional market history file found yet. Run the updated update_data.py so data/regional_market_history_24h.csv is created."
    )
else:
    regional_history_df["SETTLEMENTDATE"] = pd.to_datetime(regional_history_df["SETTLEMENTDATE"], errors="coerce")
    for col in ["RENEWABLE_DEMAND_DELTA_MW", "BATTERY_CHARGING_MW", "RENEWABLE_GEN_MW", "TOTALDEMAND", "RRP"]:
        if col in regional_history_df.columns:
            regional_history_df[col] = pd.to_numeric(regional_history_df[col], errors="coerce")

    regional_history_df = regional_history_df.dropna(subset=["SETTLEMENTDATE", "REGIONID"])

    if regional_history_df.empty or "RENEWABLE_DEMAND_DELTA_MW" not in regional_history_df.columns:
        st.info("Regional history is present, but it does not yet contain the renewable/demand delta columns. Run the updated updater once.")
    else:
        available_regions = sorted(regional_history_df["REGIONID"].dropna().astype(str).unique())
        selected_asset_region = str(selected_row.get("Region", ""))
        default_region_index = available_regions.index(selected_asset_region) if selected_asset_region in available_regions else 0

        selected_region_for_chart = st.selectbox(
            "Select region for renewable/demand vs battery charging chart",
            available_regions,
            index=default_region_index,
        )

        region_chart_df = regional_history_df[
            regional_history_df["REGIONID"].astype(str) == selected_region_for_chart
        ].copy()
        region_chart_df = region_chart_df.sort_values("SETTLEMENTDATE")

        newest_time = region_chart_df["SETTLEMENTDATE"].max()
        cutoff = newest_time - pd.Timedelta(hours=24)
        region_chart_df = region_chart_df[region_chart_df["SETTLEMENTDATE"] >= cutoff].copy()

        if region_chart_df.empty:
            st.info("No cached regional rows found for this region yet.")
        else:
            chart_source = region_chart_df[[
                "SETTLEMENTDATE",
                "RENEWABLE_DEMAND_DELTA_MW",
                "BATTERY_CHARGING_MW",
            ]].copy()
            chart_source = chart_source.rename(columns={
                "SETTLEMENTDATE": "Time",
                "RENEWABLE_DEMAND_DELTA_MW": "Renewables - demand MW",
                "BATTERY_CHARGING_MW": "Battery charging MW",
            })
            chart_long = chart_source.melt(
                id_vars="Time",
                var_name="Metric",
                value_name="MW",
            ).dropna(subset=["MW"])

            y_min = min(float(chart_long["MW"].min()), 0.0)
            y_max = max(float(chart_long["MW"].max()), 0.0)
            pad = max((y_max - y_min) * 0.12, 50.0)

            regional_line = alt.Chart(chart_long).mark_line(
                strokeWidth=3,
                interpolate="monotone",
            ).encode(
                x=alt.X("Time:T", title="Time", axis=alt.Axis(labelColor="#d6a095", titleColor="#f4d8cf", gridColor="rgba(255,105,56,0.12)")),
                y=alt.Y("MW:Q", title="MW", scale=alt.Scale(domain=[y_min - pad, y_max + pad]), axis=alt.Axis(labelColor="#d6a095", titleColor="#f4d8cf", gridColor="rgba(255,105,56,0.16)")),
                color=alt.Color(
                    "Metric:N",
                    scale=alt.Scale(range=["#ff6938", "#f4d8cf"]),
                    legend=alt.Legend(labelColor="#f4d8cf", titleColor="#f4d8cf"),
                ),
                tooltip=[
                    alt.Tooltip("Time:T", title="Time"),
                    alt.Tooltip("Metric:N", title="Metric"),
                    alt.Tooltip("MW:Q", title="MW", format=",.1f"),
                ],
            )

            zero_rule = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
                color="#d6a095",
                opacity=0.55,
                strokeDash=[5, 5],
            ).encode(y="y:Q")

            regional_chart = (zero_rule + regional_line).properties(
                height=340,
                background="rgba(99, 39, 32, 0.86)",
                title={
                    "text": f"{selected_region_for_chart} — renewable surplus/shortfall vs BESS charging",
                    "subtitle": "Renewables - demand uses grid-scale SCADA renewables where Full NEM Plant Registration.csv is available. Battery charging is total BESS import MW.",
                    "color": "#f4d8cf",
                    "subtitleColor": "#d6a095",
                    "font": "Inter",
                    "fontSize": 18,
                    "anchor": "start",
                },
            ).configure_view(
                stroke="rgba(255,105,56,0.35)"
            ).configure_axis(
                labelFont="Inter",
                titleFont="Inter",
                domainColor="rgba(255,105,56,0.30)",
                tickColor="rgba(255,105,56,0.30)",
            )

            st.altair_chart(regional_chart, use_container_width=True)


# ---------------- LEADERBOARD ----------------
leaderboard = df[[
    "asset_label",
    "Region",
    "BESS_STATE",
    "SIGNED_MW",
    "ABS_MW",  # kept only for sorting, removed before display
    "REGION_RRP",
    "STORAGE_MWH",
    "utilisation_pct",
]].sort_values("ABS_MW", ascending=False).head(10)

leaderboard = leaderboard.drop(columns=["ABS_MW"], errors="ignore")
leaderboard = leaderboard.rename(columns={
    "asset_label": "Asset",
    "BESS_STATE": "State",
    "SIGNED_MW": "Signed MW",
    "REGION_RRP": "Regional Price $/MWh",
    "STORAGE_MWH": "Storage MWh",
    "utilisation_pct": "Utilisation %",
})

st.markdown(
    """
    <div class="section-title"><span class="highlight">Most active</span> BESS assets right now</div>
    """,
    unsafe_allow_html=True,
)
st.dataframe(leaderboard, use_container_width=True, hide_index=True)
