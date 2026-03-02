import json
import time
from collections import defaultdict
from typing import Callable, Optional, Tuple

import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from geopy.geocoders import Nominatim
import streamlit as st
from streamlit_folium import st_folium


def is_kansas(lat, lon) -> bool:
    "Return True if (lat,lon) is inside Kansas bounds."
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return False

    return (36.99 <= lat <= 40.01) and (-102.06 <= lon <= -94.58)


def is_valid_coordinate(lat, lon) -> bool:
    "Check lat/lon can convert to float, is within range, and not 0,0."
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return False

    if pd.isna(lat) or pd.isna(lon):
        return False

    if abs(lat) > 90 or abs(lon) > 180:
        return False

    if lat == 0 and lon == 0:
        return False

    return True


def clean_donation(value):
    "Parse a donation string to float, return 0 if missing/invalid."
    if pd.isna(value):
        return 0
    value = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except Exception:
        return 0


def geocode_records(
    records,
    limit: int = 100,
    delay: float = 0.2,
    cache_path: str = "geocode_cache.json",
    progress: Optional[Callable[[int], None]] = None,
    status: Optional[Callable[[str], None]] = None,
) -> None:
    "Geocode address dicts (City/State/Country) in-place; cache results."

    try:
        with open(cache_path, "r") as f:
            cache = json.load(f)
    except FileNotFoundError:
        cache = {}

    geolocator = Nominatim(user_agent="heatmap_script", timeout=10)

    total = min(limit, len(records))
    for idx, entry in enumerate(records[:limit], start=1):

        # helper to safely coerce values to stripped strings
        def _safe_strip(v):
            if v is None:
                return ""
            try:
                s = str(v)
            except Exception:
                return ""
            s = s.strip()
            if s.lower() in ("nan", "none"):
                return ""
            return s

        # prefer City,State,Country; fall back to Zip+Country or State+Country
        country = _safe_strip(entry.get("Country")) or "USA"
        city = _safe_strip(entry.get("City"))
        state = _safe_strip(entry.get("State"))
        zip_code = _safe_strip(entry.get("Zip") or entry.get("zip") or entry.get("Postal"))

        if city and state:
            query = f"{city}, {state}, {country}"
        elif zip_code:
            query = f"{zip_code}, {country}"
        elif state:
            query = f"{state}, {country}"
        else:
            query = country

        if query in cache:
            entry["Latitude"], entry["Longitude"] = cache[query]
            continue

        try:
            loc = geolocator.geocode(query)
            if loc:
                lat, lon = loc.latitude, loc.longitude
            else:
                lat, lon = None, None
        except Exception:
            lat, lon = None, None

        cache[query] = (lat, lon)
        entry["Latitude"], entry["Longitude"] = lat, lon

        time.sleep(delay)

        if progress:
            progress(int(idx / total * 100))
        if status and idx % 10 == 0:
            status(f"Geocoded {idx}/{total} locations...")

    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


def build_map_from_df(df: pd.DataFrame) -> Tuple[folium.Map, int, int]:
    """Generate a folium map from df, skipping invalid/Kansas coords.

    Returns map plus counts of invalid and Kansas rows.
    """

    counts = defaultdict(float)
    invalid_count = 0
    kansas_count = 0

    for _, row in df.iterrows():

        lat = row.get("Latitude")
        lon = row.get("Longitude")
        donation = clean_donation(row.get("Donations"))

        if not is_valid_coordinate(lat, lon):
            invalid_count += 1
            continue

        if is_kansas(lat, lon):
            kansas_count += 1
            continue

        counts[(float(lat), float(lon))] += donation

    m = folium.Map(
        location=[40.7128, -74.0060],
        zoom_start=5,
    )

    cluster_group = MarkerCluster().add_to(m)

    for (lat, lon), total in counts.items():
        folium.Marker(
            location=[lat, lon],
            popup=f"${total:,.2f} donated here",
        ).add_to(cluster_group)

    heat_points = [[lat, lon, total] for (lat, lon), total in counts.items()]
    if heat_points:
        HeatMap(heat_points, radius=25, blur=20).add_to(m)

    return m, invalid_count, kansas_count


def render_heatmap(
    df: pd.DataFrame,
    cache_path: str = "geocode_cache.json",
    geocode_limit: int = 10000,
) -> None:
    """Render Streamlit heatmap, geocoding if needed, with progress."""

    st.subheader("Donor Heatmap")

    if df.empty:
        st.info("No data available.")
        return

    work_df = df.copy()

    work_df.columns = [c.strip() for c in work_df.columns]
    lower_map = {c.lower(): c for c in work_df.columns}

    city_col = lower_map.get("city")
    state_col = lower_map.get("state")
    country_col = lower_map.get("country")
    zip_col = lower_map.get("zip") or lower_map.get("zip code") or lower_map.get("postal code") or lower_map.get("postal")

    has_latlon = "Latitude" in work_df.columns and "Longitude" in work_df.columns
    # consider address present if city+state+country OR zip+country
    has_address = (city_col and state_col and country_col) or (zip_col and country_col)

    if not has_latlon and not has_address:
        st.error("Heatmap requires city/state/country or lat/lon columns.")
        return

    if not has_latlon and has_address:

        records = []

        for _, row in work_df.iterrows():
            records.append({
                "City": row.get(city_col, ""),
                "State": row.get(state_col, ""),
                "Country": row.get(country_col, ""),
                "Zip": row.get(zip_col, "") if zip_col else "",
                "Latitude": None,
                "Longitude": None,
            })

        progress_bar = st.progress(0)

        def update_progress(pct):
            progress_bar.progress(pct)

        geocode_records(
            records,
            limit=min(geocode_limit, len(records)),
            delay=0.2,
            cache_path=cache_path,
            progress=update_progress,
        )

        work_df["Latitude"] = [r["Latitude"] for r in records]
        work_df["Longitude"] = [r["Longitude"] for r in records]

    m, invalid_count, kansas_count = build_map_from_df(work_df)

    st_folium(m, width=900, height=600)

    st.caption(
        f"Excluded {invalid_count} invalid locations and "
        f"{kansas_count} Kansas fallback locations."
    )


if __name__ == "__main__":

    # Determine CSV path: argument > local file > data/ directory
    import sys, os

    csv_path = None
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        for candidate in [
            "NYCFBiokindData_Sheet1.csv",
            os.path.join("data", "NYCFBiokindData_Sheet1.csv"),
        ]:
            if os.path.isfile(candidate):
                csv_path = candidate
                break

    if not csv_path:
        raise FileNotFoundError(
            "CSV file not found. Provide path as first arg or place "
            "NYCFBiokindData_Sheet1.csv in this directory or data/."
        )

    df = pd.read_csv(csv_path)
    render_heatmap(df)