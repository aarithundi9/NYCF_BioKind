
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
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return False

    return (36.99 <= lat <= 40.01) and (-102.06 <= lon <= -94.58)



def is_valid_coordinate(lat, lon) -> bool:
    """Basic sanity checks for coordinates, including NaNs."""
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return False

    # reject NaNs
    if pd.isna(lat) or pd.isna(lon):
        return False

    # reject extreme impossible values
    if abs(lat) > 90 or abs(lon) > 180:
        return False

    # reject (0,0)
    if lat == 0 and lon == 0:
        return False

    return True


def geocode_records(
    records,
    limit: int = 100,
    delay: float = 0.2,
    cache_path: str = "scripts/Kevin/geocode_cache.json",
    progress: Optional[Callable[[int], None]] = None,
    status: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Mutates `records` (list of dicts) in place by filling Latitude / Longitude.
    Uses Nominatim + a JSON cache.
    """
    try:
        with open(cache_path, "r") as f:
            cache = json.load(f)
    except FileNotFoundError:
        cache = {}

    geolocator = Nominatim(user_agent="heatmap_script", timeout=10)

    total = min(limit, len(records))
    for idx, entry in enumerate(records[:limit], start=1):
        query = f"{entry['City']}, {entry['State']}, {entry['Country']}"

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
    """
    Given a DataFrame with Latitude / Longitude, build the Folium map and
    return (map, invalid_count, kansas_count).
    """
    counts = defaultdict(int)
    invalid_count = 0
    kansas_count = 0

    for _, row in df.iterrows():
        lat = row.get("Latitude")
        lon = row.get("Longitude")

        if not is_valid_coordinate(lat, lon):
            invalid_count += 1
            continue

        if is_kansas(lat, lon):
            kansas_count += 1
            continue

        counts[(float(lat), float(lon))] += 1

    # Base map
    m = folium.Map(
        location=[40.7128, -74.0060],
        zoom_start=5,
        max_bounds=True,
        world_copy_jump=False,
    )

    # Sidebar legend
    legend_html = f"""
    <div style="
        position: fixed; 
        top: 50px; 
        left: 50px; 
        background-color: #ffffff;
        border-radius: 10px;
        padding: 16px 18px;
        width: 300px;
        font-size: 14px;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border: 1px solid #d0d0d0;
        font-family: 'Inter', sans-serif;
    ">
        <div style="
            font-weight: 600;
            font-size: 15px;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid #eee;
        ">
            Unmapped Entries Summary
        </div>

        <div style="margin-bottom: 6px;">
            <span style="color:#444;">Missing Geocodes:</span>
            <span style="float:right; color:#c0392b; font-weight:600;">{invalid_count}</span>
        </div>

        <div style="margin-bottom: 6px;">
            <span style="color:#444;">Kansas FallBack Removed:</span>
            <span style="float:right; color:#c0392b; font-weight:600;">{kansas_count}</span>
        </div>

        <div style="
            margin-top: 12px;
            padding-top: 8px;
            border-top: 1px solid #eee;
            font-weight: 600;
            color:#1d4ed8;
        ">
            Total excluded:
            <span style="float:right;">{invalid_count + kansas_count}</span>
        </div>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    # Cluster JS using encoded class donor-XX
    cluster_js = """
    function(cluster) {
        var markers = cluster.getAllChildMarkers();
        var total = 0;

        markers.forEach(function(m) {
            var cls = m.options.icon.options.className;
            var match = cls.match(/donor-(\\d+)/);
            if (match) {
                total += parseInt(match[1]);
            }
        });

        var color = "blue";
        if (total < 11) color = "green";
        else if (total < 51) color = "blue";
        else if (total < 151) color = "orange";
        else color = "red";

        return L.divIcon({
            html: '<div style="background-color:' + color +
                  '; border-radius:20px; width:40px; height:40px; display:flex; ' +
                  'align-items:center; justify-content:center; color:white; ' +
                  'font-weight:bold;">' + total + '</div>',
            className: 'donor-cluster',
            iconSize: new L.Point(40, 40)
        });
    }
    """

    cluster_group = MarkerCluster(icon_create_function=cluster_js).add_to(m)

    # Add real markers
    for (lat, lon), num in counts.items():
        folium.Marker(
            location=[lat, lon],
            popup=f"{num} donor(s) here",
            icon=folium.Icon(color="blue", class_name=f"donor-{num}"),
        ).add_to(cluster_group)

    # Heatmap
    heat_points = [[lat, lon, num] for (lat, lon), num in counts.items()]
    if heat_points:
        HeatMap(heat_points, radius=20, blur=15).add_to(m)

    return m, invalid_count, kansas_count


def render_heatmap(
    df: pd.DataFrame,
    cache_path: str = "scripts/Kevin/geocode_cache.json",
    geocode_limit: int = 10_000,
) -> None:
    """
    Streamlit-friendly function:
    - Requires either Latitude/Longitude OR City/State/Country in df.
    - Geocodes missing Lat/Lon using cache.
    - Renders the Folium map inside Streamlit.
    """
    st.subheader("Donor Heatmap")

    if df.empty:
        st.info("No data available for heatmap.")
        return

    # Work on a copy so we don't mutate session_state data
    work_df = df.copy()

    has_latlon = "Latitude" in work_df.columns and "Longitude" in work_df.columns
    has_address = all(col in work_df.columns for col in ["City", "State", "Country"])

    if not has_latlon and not has_address:
        st.error(
            "Heatmap requires either Latitude/Longitude columns "
            "or City/State/Country columns."
        )
        return

    # If we don't have Lat/Lon, geocode based on City/State/Country
    if not has_latlon and has_address:
        records = []
        for _, row in work_df.iterrows():
            entry = {
                "City": row.get("City", ""),
                "State": row.get("State", ""),
                "Country": row.get("Country", ""),
                "Latitude": None,
                "Longitude": None,
            }
            records.append(entry)

        progress_bar = st.progress(0, text="Geocoding donor locations (with cache)...")
        status = st.empty()

        def update_progress(pct: int) -> None:
            progress_bar.progress(pct, text=f"Geocoding donor locations (with cache)... {pct}%")

        def update_status(msg: str) -> None:
            status.write(msg)

        geocode_records(
            records,
            limit=min(geocode_limit, len(records)),
            delay=0.2,
            cache_path=cache_path,
            progress=update_progress,
            status=update_status,
        )

        progress_bar.progress(100, text="Geocoding complete.")
        status.empty()

        work_df["Latitude"] = [r["Latitude"] for r in records]
        work_df["Longitude"] = [r["Longitude"] for r in records]

    # Build and render the map
    m, invalid_count, kansas_count = build_map_from_df(work_df)

    st_folium(m, width=900, height=600)
    st.caption(
        f"Excluded {invalid_count} invalid locations and "
        f"{kansas_count} Kansas fallback locations."
    )


# Optional: keep a CLI entrypoint if you still want to generate the HTML file directly.
if __name__ == "__main__":
    # Example: if you still want to run `python heatmap.py` to get an HTML file
    import csv

    filename = "data/Riverkeeper_Donors.csv"
    records = []

    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                "City": row.get("City", ""),
                "State": row.get("State", ""),
                "Country": row.get("Country", ""),
                "Latitude": None,
                "Longitude": None,
            }
            records.append(entry)

    geocode_records(records, limit=len(records), delay=0.2)
    df_cli = pd.DataFrame(records)
    m_cli, _, _ = build_map_from_df(df_cli)
    m_cli.save("scripts/Kevin/donor_map.html")
    print("Saved map to scripts/Kevin/donor_map.html")
