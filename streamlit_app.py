import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# styling
st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com');

    .stMarkdown, p, label, .stSelectbox {
            font-family: "Inter", sans-serif !important;
    }

    .stApp {
        background: RGBA(68, 159, 186, 1);
        background: linear-gradient(180deg, rgba(68, 159, 186, 0.9) 7%, rgba(239, 208, 187, 0.9) 86%);
        background-attachment: fixed;
    }

    .hero {
        background: linear-gradient(90deg, rgba(225, 169, 131, 1) 9%, rgba(202, 94, 47, 1) 67%); 
        padding: 30px 20px;
        border-radius: 12px;
        margin-bottom: 25px;
        text-align: center;
        background-size: cover;
        background-position: center;
        box-shadow: 2px 4px 14px 5px rgba(86,47,20,0.39);
    }

    .hero h1 {
        color: #EFD0BB;
        font-family: 'Garamond', serif;
        font-weight: 700;
        font-size: 2.2rem; 
        margin: 0;
        text-shadow: 2px 4px 14px 5px rgba(86,47,20,0.39);
    }

    .content-card {
        background-color: white !important;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
        color: #31333F !important;
        overflow-x: auto;
    }

    .custom-text {
        color: #31333F; 
        font-size: 35px;
        font-weight: bold;
        margin-top: 20px;
    }
    
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .custom-table th {
        text-align: left;
        padding: 12px 8px;
        background-color: #e1a983;
        color: black;
        border-bottom: 2px solid #f0f2f6;
        width: 100%;
        table-layout: auto;
    }
    .custom-table td {
        padding: 12px 8px;
        border-bottom: 1px solid #f0f2f6;
        color: #31333F;
    }

    @media (max-width: 768px) {
        .table-wrapper {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        .custom-table {
            min-width: 700px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# loading DATA
DATA_URL = (
    "https://github.com/rshaw13/au_bess_map.git/refs/heads/main/data/latest_bess_data.csv"
)

@st.cache_data(ttl=300)
def load_data():
    return pd.read_csv(DATA_URL)


df = load_data()

# Defensive cleanup
if df.empty:
    st.error("No BESS data found. Run update_data.py first and check data/latest_bess_data.csv was created.")
    st.stop()

# title and linkedin caption
st.markdown(
    """
    <div class="hero">
        <h1>Australian BESS Live Dispatch Map</h1>
    </div>
    """,
    unsafe_allow_html=True
)

linkedin_url = "https://www.linkedin.com/in/ryan-shaw13/"
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: #0a0a0a; font-size: 0.85rem;">
        <div>An energy project by Ryan Shaw.</div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span>Contact me on LinkedIn: </span>
            <a href="{linkedin_url}" target="_blank">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/LinkedIn_icon.svg/250px-LinkedIn_icon.svg.png" width="18px">
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('<p class="custom-text"><strong>Current Battery Dispatch Map</strong></p>', unsafe_allow_html=True)

# Top-level commercial summary
charging_mw = df.loc[df["SIGNED_MW"] < -1, "ABS_MW"].sum()
discharging_mw = df.loc[df["SIGNED_MW"] > 1, "ABS_MW"].sum()
idle_count = (df["BESS_STATE"] == "Idle").sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total discharging", f"{discharging_mw:,.1f} MW")
col2.metric("Total charging", f"{charging_mw:,.1f} MW")
col3.metric("Idle / near idle assets", f"{idle_count}")

# BESS selector
selected_label = st.selectbox(
    "Hover over a battery on the map to find its name, then use the drop-down to select a BESS asset for dispatch information below.",
    df["asset_label"].sort_values().unique()
)

selected_row = df[df["asset_label"] == selected_label].iloc[0]

# setting up folium map
m = folium.Map(
    location=[-30, 145],
    zoom_start=4.5,
    tiles="CartoDB positron",
    width='100%',
    height='100%'
)

# BESS output is often small relative to capacity, so used a base radius.
# Marker fill radius = actual abs MW. Ring radius = max discharge capacity.
scale = 0.10
min_radius = 4

def state_colour(state: str, is_selected: bool = False) -> str:
    if is_selected:
        return "#FC0C3B"
    if state == "Discharging":
        return "#ca5e2f"   # orange/red = exporting
    if state == "Charging":
        return "#449fba"   # blue = importing/charging
    return "#808080"       # grey = idle

# BESS markers
for _, row in df.iterrows():
    is_selected = row["asset_label"] == selected_label
    marker_radius = max(min_radius, row["ABS_MW"] * scale)
    capacity_radius = max(min_radius + 2, row["MAX_DISCHARGE_MW"] * scale)

    popup_text = f"""
        <b>{row['Station Name']}</b><br>
        DUID: {row['DUID']}<br>
        Region: {row['Region']}<br>
        State: {row['BESS_STATE']}<br>
        Signed dispatch: {row['SIGNED_MW']:.1f} MW<br>
        Discharge capacity: {row['MAX_DISCHARGE_MW']:.1f} MW<br>
        Charge capacity: {row['MAX_CHARGE_MW']:.1f} MW<br>
        Storage: {row['STORAGE_MWH']:.1f} MWh<br>
        Utilisation: {row['utilisation_pct']:.1f}%
        """

    # Actual active MW marker
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=marker_radius,
        fill=True,
        fill_opacity=0.65,
        fill_color=state_colour(row["BESS_STATE"], is_selected),
        color=state_colour(row["BESS_STATE"], is_selected),
        weight=1,
        tooltip=row['asset_label'],
        popup=popup_text,
    ).add_to(m)

    # Capacity ring
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=capacity_radius,
        color="gray",
        weight=1,
        fill=True,
        fill_opacity=0.18 if is_selected else 0,
        fill_color="#FC0C3B",
        tooltip=row['asset_label'],
        popup=popup_text,
    ).add_to(m)

# render map
map_data = st_folium(
    m,
    width=None,
    height=450 if st.session_state.get("is_mobile", False) else 600,
    key="bess_map",
)

st.caption(
    f"Last update (Aus Time): {df['SETTLEMENTDATE'].iloc[0]} - latest public AEMO Dispatch_SCADA data can lag real time. "
    "Positive MW = discharging/exporting; negative MW = charging/importing."
)

# selection-specific BESS data table
table_df = pd.DataFrame([{
    "BESS Asset": str(selected_row["Station Name"]),
    "DUID": str(selected_row["DUID"]),
    "Region": str(selected_row["Region"]),
    "State": str(selected_row["BESS_STATE"]),
    "Signed Dispatch (MW)": float(round(selected_row["SIGNED_MW"], 1)),
    "Abs Dispatch (MW)": float(round(selected_row["ABS_MW"], 1)),
    "Discharge Capacity (MW)": float(round(selected_row["MAX_DISCHARGE_MW"], 1)),
    "Charge Capacity (MW)": float(round(selected_row["MAX_CHARGE_MW"], 1)),
    "Storage Capacity (MWh)": float(round(selected_row["STORAGE_MWH"], 1)),
    "Utilisation (%)": float(round(selected_row["utilisation_pct"], 0)),
    "Last Update (Aus Time)": str(selected_row["SETTLEMENTDATE"]),
}])

table_df = table_df.astype(object)
table_html = table_df.to_html(index=False, classes='custom-table')

st.markdown(
    f"""
    <div class="content-card">
        <h3 style="color: #31333F;">Selected BESS Asset Details</h3>
        <div class="table-wrapper">
            {table_html}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Simple leaderboard to add commercial flavour without changing the data pipeline
leaderboard = df[[
    "asset_label",
    "Region",
    "BESS_STATE",
    "SIGNED_MW",
    "ABS_MW",
    "MAX_DISCHARGE_MW",
    "MAX_CHARGE_MW",
    "STORAGE_MWH",
    "utilisation_pct",
]].sort_values("ABS_MW", ascending=False).head(10)

leaderboard = leaderboard.rename(columns={
    "asset_label": "Asset",
    "BESS_STATE": "State",
    "SIGNED_MW": "Signed MW",
    "ABS_MW": "Abs MW",
    "MAX_DISCHARGE_MW": "Discharge MW",
    "MAX_CHARGE_MW": "Charge MW",
    "STORAGE_MWH": "Storage MWh",
    "utilisation_pct": "Utilisation %",
})

st.markdown(
    """
    <div class="content-card">
        <h3 style="color: #31333F;">Most Active BESS Assets Right Now</h3>
    </div>
    """,
    unsafe_allow_html=True
)
st.dataframe(leaderboard, use_container_width=True, hide_index=True)
