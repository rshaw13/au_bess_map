import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ---------------- CONFIG ----------------
SCADA_INDEX_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/Dispatch_SCADA/"
DISPATCHIS_INDEX_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/DispatchIS_Reports/"

# Required for BESS metadata
BESS_SPEC_FILE = "full_bess_specifications.csv"

# Optional, but needed for renewable-generation-vs-demand chart.
# This can be the same full registration CSV you used in the old wind repo.
FULL_REGISTRATION_FILE = "Full NEM Plant Registration.csv"

OUTPUT_FILE = "data/latest_bess_data.csv"
HISTORY_FILE = "data/bess_history_24h.csv"

MARKET_OUTPUT_FILE = "data/latest_regional_market_data.csv"
MARKET_HISTORY_FILE = "data/regional_market_history_24h.csv"

HISTORY_HOURS = 24

RENEWABLE_FUEL_KEYWORDS = (
    "Wind",
    "Solar",
    "Hydro",
    "Water",
    "Biomass",
    "Biogas",
)
# ----------------------------------------


def get_latest_zip_url(index_url: str, filename_contains: str) -> str:
    """Return the latest matching zip from a NEMWEB directory listing."""
    r = requests.get(index_url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    zip_links = [
        a["href"]
        for a in soup.find_all("a", href=True)
        if filename_contains in a["href"] and a["href"].endswith(".zip")
    ]

    if not zip_links:
        raise RuntimeError(f"No {filename_contains} zip files found at {index_url}")

    zip_links.sort(reverse=True)
    return urljoin(index_url, zip_links[0])


def get_latest_scada_url() -> str:
    return get_latest_zip_url(SCADA_INDEX_URL, "PUBLIC_DISPATCHSCADA")


def get_latest_dispatchis_url() -> str:
    return get_latest_zip_url(DISPATCHIS_INDEX_URL, "PUBLIC_DISPATCHIS")


def get_latest_scada(zip_url: str) -> pd.DataFrame:
    r = requests.get(zip_url, timeout=30)
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            df = pd.read_csv(f)

    df.columns = df.iloc[0]
    df = df.iloc[1:-1][["SETTLEMENTDATE", "DUID", "SCADAVALUE"]]
    df["SCADAVALUE"] = pd.to_numeric(df["SCADAVALUE"], errors="coerce").round(2)
    df = df.dropna(subset=["SCADAVALUE"])
    return df


def read_mms_zip_tables(zip_url: str) -> dict[str, pd.DataFrame]:
    """Read an AEMO MMS-format zip and return each table as a dataframe.

    MMS CSVs contain metadata rows plus header rows beginning with I and data
    rows beginning with D. This parser keeps the same first four metadata
    fields as the table key, then maps D rows onto the corresponding I header.
    """
    r = requests.get(zip_url, timeout=30)
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig", newline="")
            rows = list(csv.reader(text))

    headers: dict[tuple[str, ...], list[str]] = {}
    data_rows: dict[tuple[str, ...], list[list[str]]] = {}

    for row in rows:
        if len(row) < 5:
            continue

        row_type = row[0]
        table_key = tuple(row[1:4])

        if row_type == "I":
            headers[table_key] = row[4:]
            data_rows.setdefault(table_key, [])
        elif row_type == "D" and table_key in headers:
            data_rows.setdefault(table_key, []).append(row[4:])

    tables: dict[str, pd.DataFrame] = {}
    for key, header in headers.items():
        rows_for_table = data_rows.get(key, [])
        if not rows_for_table:
            continue

        width = len(header)
        normalised_rows = []
        for row in rows_for_table:
            if len(row) < width:
                row = row + [None] * (width - len(row))
            normalised_rows.append(row[:width])

        name = "|".join(key)
        tables[name] = pd.DataFrame(normalised_rows, columns=header)

    return tables


def find_table(tables: dict[str, pd.DataFrame], required_cols: list[str]) -> pd.DataFrame:
    required = set(required_cols)
    for _, table in tables.items():
        if required.issubset(set(table.columns)):
            return table.copy()
    available = {name: list(df.columns)[:15] for name, df in tables.items()}
    raise RuntimeError(f"Could not find table with columns {required_cols}. Available table starts: {available}")


def get_latest_regional_market_data(dispatchis_url: str) -> pd.DataFrame:
    """Fetch latest region price and demand from DispatchIS_Reports."""
    tables = read_mms_zip_tables(dispatchis_url)

    price = find_table(tables, ["SETTLEMENTDATE", "REGIONID", "RRP"])
    demand = find_table(tables, ["SETTLEMENTDATE", "REGIONID", "TOTALDEMAND"])

    price = price[["SETTLEMENTDATE", "REGIONID", "RRP"]].copy()
    demand = demand[["SETTLEMENTDATE", "REGIONID", "TOTALDEMAND"]].copy()

    for frame in [price, demand]:
        frame["SETTLEMENTDATE"] = pd.to_datetime(frame["SETTLEMENTDATE"], errors="coerce")
        frame["REGIONID"] = frame["REGIONID"].astype(str).str.strip()

    price["RRP"] = pd.to_numeric(price["RRP"], errors="coerce")
    demand["TOTALDEMAND"] = pd.to_numeric(demand["TOTALDEMAND"], errors="coerce")

    market = price.merge(demand, on=["SETTLEMENTDATE", "REGIONID"], how="outer")
    market = market.dropna(subset=["SETTLEMENTDATE", "REGIONID"])

    # Keep one row per region for the latest dispatch interval in this file.
    latest_interval = market["SETTLEMENTDATE"].max()
    market = market[market["SETTLEMENTDATE"] == latest_interval].copy()

    market["timestamp_utc"] = datetime.utcnow().isoformat()
    market = market.sort_values("REGIONID")
    return market


def classify_bess_state(signed_mw: float) -> str:
    if signed_mw > 1:
        return "Discharging"
    if signed_mw < -1:
        return "Charging"
    return "Idle"


def build_bess_dataset(scada: pd.DataFrame, regional_market: pd.DataFrame | None = None) -> pd.DataFrame:
    bess = pd.read_csv(BESS_SPEC_FILE)

    keep_cols = [
        "Participant",
        "Station Name",
        "Region",
        "Dispatch Type",
        "Category",
        "Fuel Source - Primary",
        "Technology Type - Primary",
        "DUID",
        "Max Cap generation (MW)",
        "Max Cap consumption (MW)",
        "Maximum storage capacity",
        "Latitude",
        "Longitude",
    ]
    bess = bess[keep_cols].copy()

    bess = bess[
        bess["Fuel Source - Primary"].str.contains("Battery", case=False, na=False)
        | bess["Technology Type - Primary"].str.contains("Storage", case=False, na=False)
    ].copy()

    bess = bess.rename(
        columns={
            "Max Cap generation (MW)": "MAX_DISCHARGE_MW",
            "Max Cap consumption (MW)": "MAX_CHARGE_MW",
            "Maximum storage capacity": "STORAGE_MWH",
        }
    )

    for col in ["MAX_DISCHARGE_MW", "MAX_CHARGE_MW", "STORAGE_MWH", "Latitude", "Longitude"]:
        bess[col] = pd.to_numeric(bess[col], errors="coerce")

    bess["MAX_CHARGE_MW"] = bess["MAX_CHARGE_MW"].fillna(bess["MAX_DISCHARGE_MW"])
    bess["STORAGE_MWH"] = bess["STORAGE_MWH"].fillna(0)

    merged = scada.merge(bess, on="DUID", how="inner")

    is_load_duid = merged["Dispatch Type"].str.contains("Load", case=False, na=False)
    merged["SIGNED_MW"] = merged["SCADAVALUE"]
    merged.loc[is_load_duid, "SIGNED_MW"] = -merged.loc[is_load_duid, "SCADAVALUE"].abs()
    merged["SIGNED_MW"] = merged["SIGNED_MW"].round(2)

    merged["BESS_STATE"] = merged["SIGNED_MW"].apply(classify_bess_state)
    merged["ABS_MW"] = merged["SIGNED_MW"].abs().round(2)

    active_cap = merged["MAX_DISCHARGE_MW"].where(merged["SIGNED_MW"] >= 0, merged["MAX_CHARGE_MW"])
    merged["utilisation_pct"] = (
        merged["ABS_MW"] / active_cap * 100
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)

    merged["asset_label"] = merged["Station Name"] + " (" + merged["DUID"] + ")"
    merged["timestamp_utc"] = datetime.utcnow().isoformat()

    if regional_market is not None and not regional_market.empty:
        market_cols = regional_market[["REGIONID", "RRP", "TOTALDEMAND"]].copy()
        market_cols = market_cols.rename(columns={"REGIONID": "Region", "RRP": "REGION_RRP", "TOTALDEMAND": "REGION_TOTALDEMAND"})
        merged = merged.merge(market_cols, on="Region", how="left")
    else:
        merged["REGION_RRP"] = pd.NA
        merged["REGION_TOTALDEMAND"] = pd.NA

    preferred = [
        "SETTLEMENTDATE",
        "timestamp_utc",
        "asset_label",
        "Station Name",
        "DUID",
        "Region",
        "Participant",
        "Dispatch Type",
        "SCADAVALUE",
        "SIGNED_MW",
        "ABS_MW",
        "BESS_STATE",
        "REGION_RRP",
        "REGION_TOTALDEMAND",
        "MAX_DISCHARGE_MW",
        "MAX_CHARGE_MW",
        "STORAGE_MWH",
        "utilisation_pct",
        "Latitude",
        "Longitude",
    ]
    other_cols = [c for c in merged.columns if c not in preferred]
    return merged[preferred + other_cols]


def build_battery_regional_agg(bess_latest: pd.DataFrame) -> pd.DataFrame:
    battery = bess_latest.copy()
    battery["BATTERY_CHARGING_MW"] = battery["SIGNED_MW"].where(battery["SIGNED_MW"] < -1, 0).abs()
    battery["BATTERY_DISCHARGING_MW"] = battery["SIGNED_MW"].where(battery["SIGNED_MW"] > 1, 0)

    agg = battery.groupby("Region", as_index=False).agg(
        BATTERY_CHARGING_MW=("BATTERY_CHARGING_MW", "sum"),
        BATTERY_DISCHARGING_MW=("BATTERY_DISCHARGING_MW", "sum"),
    )
    return agg.rename(columns={"Region": "REGIONID"})


def build_renewable_generation_by_region(scada: pd.DataFrame) -> pd.DataFrame:
    """Sum current renewable SCADA by NEM region.

    This needs Full NEM Plant Registration.csv in the repo root. If it is not
    available, the app still works but the renewable-vs-demand chart will show
    renewable generation as unavailable/zero until this file is added.
    """
    registration_path = Path(FULL_REGISTRATION_FILE)
    if not registration_path.exists():
        print(f"WARNING: {FULL_REGISTRATION_FILE} not found. Renewable generation by region will be set to 0.")
        return pd.DataFrame(columns=["REGIONID", "RENEWABLE_GEN_MW"])

    reg = pd.read_csv(registration_path)
    reg.columns = reg.columns.str.strip()

    required = {"DUID", "Region", "Fuel Source - Primary"}
    if not required.issubset(set(reg.columns)):
        print(f"WARNING: {FULL_REGISTRATION_FILE} missing one of {required}. Renewable generation by region will be set to 0.")
        return pd.DataFrame(columns=["REGIONID", "RENEWABLE_GEN_MW"])

    fuel = reg["Fuel Source - Primary"].astype(str)
    is_renewable = fuel.str.contains("|".join(RENEWABLE_FUEL_KEYWORDS), case=False, na=False)
    is_battery = fuel.str.contains("Battery", case=False, na=False)

    renewable = reg.loc[is_renewable & ~is_battery, ["DUID", "Region", "Fuel Source - Primary"]].copy()
    renewable = renewable.drop_duplicates(subset=["DUID"])

    merged = scada.merge(renewable, on="DUID", how="inner")
    merged["SCADAVALUE"] = pd.to_numeric(merged["SCADAVALUE"], errors="coerce").fillna(0)
    merged["RENEWABLE_GEN_MW"] = merged["SCADAVALUE"].clip(lower=0)

    out = merged.groupby("Region", as_index=False)["RENEWABLE_GEN_MW"].sum()
    out = out.rename(columns={"Region": "REGIONID"})
    return out


def build_regional_market_snapshot(regional_market: pd.DataFrame, bess_latest: pd.DataFrame, scada: pd.DataFrame) -> pd.DataFrame:
    snapshot = regional_market.copy()
    battery_agg = build_battery_regional_agg(bess_latest)
    renewable_agg = build_renewable_generation_by_region(scada)

    snapshot = snapshot.merge(battery_agg, on="REGIONID", how="left")
    snapshot = snapshot.merge(renewable_agg, on="REGIONID", how="left")

    for col in ["BATTERY_CHARGING_MW", "BATTERY_DISCHARGING_MW", "RENEWABLE_GEN_MW", "TOTALDEMAND"]:
        snapshot[col] = pd.to_numeric(snapshot[col], errors="coerce").fillna(0)

    snapshot["RENEWABLE_DEMAND_DELTA_MW"] = snapshot["RENEWABLE_GEN_MW"] - snapshot["TOTALDEMAND"]
    snapshot = snapshot.sort_values("REGIONID")
    return snapshot


def update_rolling_history(latest: pd.DataFrame, history_file: str, dedupe_cols: list[str]) -> pd.DataFrame:
    history_path = Path(history_file)

    latest = latest.copy()
    latest["SETTLEMENTDATE"] = pd.to_datetime(latest["SETTLEMENTDATE"], errors="coerce")
    latest = latest.dropna(subset=["SETTLEMENTDATE"])

    if history_path.exists():
        existing = pd.read_csv(history_path)
        existing["SETTLEMENTDATE"] = pd.to_datetime(existing["SETTLEMENTDATE"], errors="coerce")
        existing = existing.dropna(subset=["SETTLEMENTDATE"])
        history = pd.concat([existing, latest], ignore_index=True)
    else:
        history = latest

    history = history.drop_duplicates(subset=dedupe_cols, keep="last")
    newest_time = history["SETTLEMENTDATE"].max()
    cutoff = newest_time - pd.Timedelta(hours=HISTORY_HOURS)
    history = history[history["SETTLEMENTDATE"] >= cutoff].copy()

    sort_cols = [c for c in dedupe_cols if c in history.columns]
    history = history.sort_values(sort_cols)
    history.to_csv(history_path, index=False)
    return history


def update_24h_history(latest: pd.DataFrame) -> pd.DataFrame:
    return update_rolling_history(latest, HISTORY_FILE, ["DUID", "SETTLEMENTDATE"])


def update_regional_market_history(latest: pd.DataFrame) -> pd.DataFrame:
    return update_rolling_history(latest, MARKET_HISTORY_FILE, ["REGIONID", "SETTLEMENTDATE"])


def main():
    Path("data").mkdir(parents=True, exist_ok=True)

    print("Fetching latest DispatchIS price/demand data...")
    dispatchis_url = get_latest_dispatchis_url()
    print(f"Using DispatchIS file: {dispatchis_url}")
    regional_market = get_latest_regional_market_data(dispatchis_url)

    print("Fetching SCADA...")
    latest_scada_url = get_latest_scada_url()
    print(f"Using SCADA file: {latest_scada_url}")
    scada = get_latest_scada(latest_scada_url)

    print("Finding BESS assets and merging price/demand context...")
    bess_latest = build_bess_dataset(scada, regional_market=regional_market)
    bess_latest.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(bess_latest)} rows → {OUTPUT_FILE}")

    bess_history = update_24h_history(bess_latest)
    print(f"Saved rolling 24h BESS history: {len(bess_history)} rows → {HISTORY_FILE}")

    print("Building regional market + renewable/demand + battery charging snapshot...")
    regional_snapshot = build_regional_market_snapshot(regional_market, bess_latest, scada)
    regional_snapshot.to_csv(MARKET_OUTPUT_FILE, index=False)
    print(f"Saved {len(regional_snapshot)} rows → {MARKET_OUTPUT_FILE}")

    regional_history = update_regional_market_history(regional_snapshot)
    print(f"Saved rolling 24h regional market history: {len(regional_history)} rows → {MARKET_HISTORY_FILE}")


if __name__ == "__main__":
    main()
