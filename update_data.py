import pandas as pd
import requests
import zipfile
import io
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path


# ---------------- CONFIG ----------------
SCADA_INDEX_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/Dispatch_SCADA/"

BESS_SPEC_FILE = "full_bess_specifications.csv"

OUTPUT_FILE = "data/latest_bess_data.csv"
# ----------------------------------------


def get_latest_scada_url() -> str:
    r = requests.get(SCADA_INDEX_URL, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    zip_links = [
        a["href"]
        for a in soup.find_all("a", href=True)
        if "PUBLIC_DISPATCHSCADA" in a["href"] and a["href"].endswith(".zip")
    ]

    if not zip_links:
        raise RuntimeError("No Dispatch_SCADA zip files found")

    zip_links.sort(reverse=True)
    return urljoin(SCADA_INDEX_URL, zip_links[0])


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


def classify_bess_state(signed_mw: float) -> str:

    # Convention used in this app:
    # +ve signed_mw = discharging/exporting to grid
    # -ve signed_mw = charging/importing from grid

    # For Bidirectional Units, AEMO SCADAVALUE may already be signed.
    # For legacy Load DUIDs, update_data converts positive load MW to negative signed MW.

    if signed_mw > 1:
        return "Discharging"
    if signed_mw < -1:
        return "Charging"
    return "Idle"


def build_bess_dataset(scada: pd.DataFrame) -> pd.DataFrame:
    bess = pd.read_csv(BESS_SPEC_FILE)

    # Standardise key columns and keep the useful commercial fields
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

    # filter for BESS assets
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

    # Some older load/generator DUID rows have no consumption/storage value.
    # Fall back to discharge capacity where needed so the map/table still work.
    bess["MAX_CHARGE_MW"] = bess["MAX_CHARGE_MW"].fillna(bess["MAX_DISCHARGE_MW"])
    bess["STORAGE_MWH"] = bess["STORAGE_MWH"].fillna(0)

    merged = scada.merge(bess, on="DUID", how="inner")

    # Convert to a battery-friendly signed MW convention.
    # Legacy Load rows usually report consumption as positive SCADAVALUE,
    # but commercially that is charging, so show it as negative MW.
    is_load_duid = merged["Dispatch Type"].str.contains("Load", case=False, na=False)
    merged["SIGNED_MW"] = merged["SCADAVALUE"]
    merged.loc[is_load_duid, "SIGNED_MW"] = -merged.loc[is_load_duid, "SCADAVALUE"].abs()
    merged["SIGNED_MW"] = merged["SIGNED_MW"].round(2)

    merged["BESS_STATE"] = merged["SIGNED_MW"].apply(classify_bess_state)
    merged["ABS_MW"] = merged["SIGNED_MW"].abs().round(2)

    active_cap = merged["MAX_DISCHARGE_MW"].where(
        merged["SIGNED_MW"] >= 0,
        merged["MAX_CHARGE_MW"],
    )
    merged["utilisation_pct"] = (merged["ABS_MW"] / active_cap * 100).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)

    merged["asset_label"] = merged["Station Name"] + " (" + merged["DUID"] + ")"
    merged["timestamp_utc"] = datetime.utcnow().isoformat()

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
        "MAX_DISCHARGE_MW",
        "MAX_CHARGE_MW",
        "STORAGE_MWH",
        "utilisation_pct",
        "Latitude",
        "Longitude",
    ]
    other_cols = [c for c in merged.columns if c not in preferred]
    return merged[preferred + other_cols]


def main():
    print("Fetching SCADA...")
    latest_url = get_latest_scada_url()
    print(f"Using SCADA file: {latest_url}")
    scada = get_latest_scada(latest_url)

    print("Finding BESS assets and merging datasets...")
    final = build_bess_dataset(scada)

    Path("data").mkdir(parents=True, exist_ok=True)
    final.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(final)} rows → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
