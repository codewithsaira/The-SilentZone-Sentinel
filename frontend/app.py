"""The SilentZone Sentinel - Unified Single-Screen Command Dashboard.
Combines Geospatial Area & Radius Flood Scanning, Silent Zone Detection, 
Multi-Agent Coordination Pipeline, Live Bidding, and PDF Report Generation into a single centralized view.
"""
import base64
import html
import math
import os
import sys
import time
from pathlib import Path

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from backend.app import database as db
except ImportError:
    from app import database as db

try:
    from frontend import auth
    from frontend.pakistan_cities import PAKISTAN_CITIES
    from frontend.pdf_report import generate_area_flood_pdf
except ImportError:
    import auth
    from pakistan_cities import PAKISTAN_CITIES
    from pdf_report import generate_area_flood_pdf

st.set_page_config(page_title="The SilentZone Sentinel", page_icon="🛡️", layout="wide")

# ------------------------------------------------------------------ CSS: Layout & Deploy Button Adjustments
st.markdown(
    """
    <style>
    /* 1. Eliminate extra top whitespace on main content, header, and sidebar */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 2rem !important;
        min-height: 2rem !important;
        z-index: 99 !important;
    }

    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.8rem !important;
        padding-right: 1.8rem !important;
        max-width: 100% !important;
    }

    [data-testid="stSidebarContent"] {
        padding-top: 1.2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    [data-testid="stSidebarHeader"] {
        display: none !important;
        height: 0px !important;
        padding: 0px !important;
        margin: 0px !important;
    }

    h1 {
        margin-top: -1.2rem !important;
        padding-top: 0rem !important;
        margin-bottom: 0.1rem !important;
        font-size: 2.1rem !important;
    }

    /* 2. Hide deploy button while preserving main menu */
    .stDeployButton,
    .stAppDeployButton,
    div[data-testid="stDeployButton"],
    button[data-testid="stDeployButton"],
    div[data-testid="stAppDeployButton"],
    button[data-testid="stAppDeployButton"],
    [data-testid="stToolbarActions"],
    [data-testid="stToolbarAction"],
    header [data-testid="stToolbarActions"],
    header [data-testid="stAppDeployButton"],
    header [data-testid="stDeployButton"],
    header div:has(> button[data-testid="stDeployButton"]),
    header div:has(> button[data-testid="stAppDeployButton"]) {
        display: none !important;
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
        max-width: 0px !important;
        max-height: 0px !important;
        overflow: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        margin: 0px !important;
        padding: 0px !important;
        border: none !important;
    }

    #MainMenu,
    [data-testid="stMainMenu"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    footer {
        display: none !important;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

import streamlit.components.v1 as components
components.html(
    """
    <script>
    function removeDeployBtn() {
        try {
            const targets = [
                '[data-testid="stDeployButton"]',
                '[data-testid="stAppDeployButton"]',
                '.stDeployButton',
                '.stAppDeployButton',
                '[data-testid="stToolbarActions"]',
                'header [data-testid="stToolbarActions"]',
                'header [data-testid="stAppDeployButton"]',
                'header [data-testid="stDeployButton"]'
            ];
            targets.forEach(selector => {
                const els = window.parent.document.querySelectorAll(selector);
                els.forEach(el => {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                    el.style.setProperty('width', '0px', 'important');
                    el.style.setProperty('height', '0px', 'important');
                });
            });
        } catch(e) {}
    }
    removeDeployBtn();
    setInterval(removeDeployBtn, 200);
    </script>
    """,
    height=0,
    width=0,
)

# ------------------------------------------------------------------ Authentication Gate
if not st.session_state.get("authenticated", False):
    auth.render_auth_page()
    st.stop()

# ------------------------------------------------------------------ Authenticated User Context
user = st.session_state.get("user", {})

API = os.getenv("KR_API", "http://localhost:8000").rstrip("/")
NEIGHBOR_COLOR = {"yes": "green", "unsure": "orange", "no": "gray", "pending": "lightblue", "timeout": "lightgray"}
AGENT_BADGE = {"Silence Radar": "🟥", "Neighbor Verification": "🟩", "Coordinator": "🟦", "System": "⚙️"}


def call(method: str, path: str, **kw):
    try:
        r = requests.request(method, f"{API}{path}", timeout=10, **kw)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.session_state["_err"] = f"{type(e).__name__}: {e}"
        return None


# ------------------------------------------------------------------ Haversine Distance & Spatial Flood Scanner
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def scan_area_and_radius(center_lat: float, center_lon: float, radius_km: float, scen: dict) -> dict:
    villages = scen.get("villages", [])
    
    in_radius = []
    for v in villages:
        dist = haversine_km(center_lat, center_lon, v["lat"], v["lon"])
        if dist <= radius_km:
            in_radius.append({**v, "distance_km": round(dist, 2)})
            
    in_radius.sort(key=lambda x: x["distance_km"])
    
    silent_zones = []
    flooded_sos = []
    safe_zones = []
    
    for v in in_radius:
        if v.get("in_flood", False):
            if v.get("sos_count", 0) == 0:
                silent_zones.append({
                    "id": f"Z-{v['id']}",
                    "village_id": v["id"],
                    "name": v["name"],
                    "lat": v["lat"],
                    "lon": v["lon"],
                    "population": v["population"],
                    "district": v.get("district", "Rajanpur"),
                    "flood_depth_m": v.get("flood_depth_m", 1.5),
                    "sos_count": 0,
                    "distance_km": v["distance_km"],
                })
            else:
                flooded_sos.append(v)
        else:
            safe_zones.append(v)
            
    total_pop_affected = sum(z["population"] for z in silent_zones) + sum(v["population"] for v in flooded_sos)
    silent_pop = sum(z["population"] for z in silent_zones)
    
    summary = {
        "total_villages": len(in_radius),
        "total_flooded": len(silent_zones) + len(flooded_sos),
        "total_silent": len(silent_zones),
        "total_safe": len(safe_zones),
        "total_pop_affected": total_pop_affected,
        "silent_pop": silent_pop,
    }
    
    return {
        "summary": summary,
        "silent_zones": silent_zones,
        "flooded_sos": flooded_sos,
        "safe_zones": safe_zones,
        "all_in_radius": in_radius,
    }


# ------------------------------------------------------------------ Sidebar Controls
st.sidebar.title("🛡️ The SilentZone Sentinel")
st.sidebar.caption("خاموش زون سینٹینیل — AI Multi-Agent Flood & Silent Zone Radar")

with st.sidebar.container(border=True):
    st.markdown(f"**👤 Operator:** {user.get('name', 'Active Operator')}")
    st.caption(f"Role: {user.get('role', 'Field Coordinator')} · `{user.get('username', 'user')}`")
    if st.button("🚪 Log Out", use_container_width=True, key="logout_btn"):
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state.pop("has_processed", None)
        st.session_state.pop("active_scan", None)
        st.session_state.pop("run_id", None)
        st.rerun()

health = call("GET", "/api/health")
if health:
    st.sidebar.success(f"Backend online · Telegram: {'LIVE' if health['telegram'] else 'simulator'} · LLM: {health['llm']}"
                       + (" · OFFLINE mode" if health["offline_mode"] else ""))
else:
    st.sidebar.error(f"Backend unreachable at {API}. Start it first.")

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Simulate SOS Signals")
active_scan_ctx = st.session_state.get("active_scan")
cur_silent_zones = active_scan_ctx.get("results", {}).get("silent_zones", []) if active_scan_ctx else []

if not active_scan_ctx or not cur_silent_zones:
    st.sidebar.info("ℹ️ No Silent Zones loaded yet. Please configure and click **'🚀 Process Flood Analysis'** to detect and select Silent Zones here.")
else:
    selected_silent = st.sidebar.multiselect(
        "Detected Silent Village(s):",
        options=cur_silent_zones,
        default=cur_silent_zones,
        format_func=lambda z: f"🟥 {z['name']} (Pop: ~{z['population']})",
        key="sos_silent_multiselect",
    )
    c1, c2 = st.sidebar.columns(2)
    if c1.button("📡 Send SOS", type="primary", use_container_width=True, key="btn_send_multi_sos"):
        if selected_silent:
            sent_names = []
            for sz in selected_silent:
                v_id = sz.get("village_id") or sz.get("id", "").replace("Z-", "")
                call("POST", "/api/sos", json={"village_id": v_id, "text": f"Emergency SOS signal from {sz['name']}"})
                sent_names.append(sz["name"])
            st.toast(f"✅ SOS broadcast sent for: {', '.join(sent_names)}!", icon="📡")
            fresh_scen = call("GET", "/api/scenario")
            if fresh_scen and active_scan_ctx:
                updated_results = scan_area_and_radius(active_scan_ctx["c_lat"], active_scan_ctx["c_lon"], active_scan_ctx["radius_km"], fresh_scen)
                active_scan_ctx["results"] = updated_results
                active_scan_ctx["summary"] = updated_results["summary"]
                st.session_state["active_scan"] = active_scan_ctx
            time.sleep(0.3)
            st.rerun()
        else:
            st.sidebar.warning("Please select at least one village.")
    if c2.button("🔄 Reset SOS", use_container_width=True, key="btn_reset_multi_sos"):
        call("POST", "/api/sos/reset")
        st.toast("🔄 SOS signals reset to default.", icon="🔄")
        fresh_scen = call("GET", "/api/scenario")
        if fresh_scen and active_scan_ctx:
            updated_results = scan_area_and_radius(active_scan_ctx["c_lat"], active_scan_ctx["c_lon"], active_scan_ctx["radius_km"], fresh_scen)
            active_scan_ctx["results"] = updated_results
            active_scan_ctx["summary"] = updated_results["summary"]
            st.session_state["active_scan"] = active_scan_ctx
        time.sleep(0.3)
        st.rerun()
    st.sidebar.caption("💡 Sending SOS signals converts cut-off silent villages into active SOS responders.")


# ------------------------------------------------------------------ Unified Single Folium Map Builder
def build_unified_map(center_lat: float, center_lon: float, radius_km: float, center_label: str, scen: dict, run: dict | None, results: dict) -> folium.Map:
    zoom = 11 if radius_km <= 20 else 10 if radius_km <= 45 else 9 if radius_km <= 75 else 8
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")

    secs = (run or {}).get("sections", {})
    verifs = secs.get("verifications", [])
    dispatch = (run or {}).get("dispatch")

    # 1. Flood Inundation Polygon Layer
    def style_flood(f):
        deep = f["properties"].get("depth_m", 1) >= 2
        return {
            "color": "#08306b" if deep else "#2171b5",
            "weight": 2,
            "fillColor": "#08519c" if deep else "#6baed6",
            "fillOpacity": 0.40 if deep else 0.25,
        }
    folium.GeoJson(
        scen["flood"],
        name="Flood Footprint",
        style_function=style_flood,
        tooltip=folium.GeoJsonTooltip(fields=["name", "depth_m"], aliases=["Flood Zone", "Depth (m)"])
    ).add_to(m)

    # 2. Search Radius Boundary Circle
    folium.Circle(
        location=[center_lat, center_lon],
        radius=radius_km * 1000,
        color="#d32f2f",
        weight=2.5,
        fill=True,
        fill_color="#ffcdd2",
        fill_opacity=0.15,
        tooltip=f"Scan Radius: {radius_km} KM around {center_label}",
    ).add_to(m)

    # 3. Target Center Point Marker
    folium.Marker(
        [center_lat, center_lon],
        icon=folium.Icon(color="darkblue", icon="bullseye", prefix="fa"),
        tooltip=f"Target: {center_label} ({center_lat:.4f}°N, {center_lon:.4f}°E)",
        popup=folium.Popup(f"<b>📍 Target Center: {html.escape(center_label)}</b><br/>Radius: {radius_km} KM", max_width=240),
    ).add_to(m)

    # 4. Silent Zones Markers & Neighbor Verification Vectors
    silent_list = results.get("silent_zones", [])
    for z in silent_list:
        v_status = z.get("verification", {}).get("status", "pending") if isinstance(z.get("verification"), dict) else "pending"
        folium.Marker(
            [z["lat"], z["lon"]],
            icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"),
            tooltip=f"🟥 SILENT ZONE: {z['name']} (~{z['population']} pop, 0 SOS)",
            popup=folium.Popup(
                f"<b>🟥 SILENT ZONE: {html.escape(z['name'])}</b><br/>"
                f"Distance: {z.get('distance_km', '-')} km<br/>"
                f"Population: ~{z['population']}<br/>"
                f"Flood Depth: {z['flood_depth_m']} m<br/>"
                f"<b>SOS Count: 0 (Cut-Off)</b><br/>"
                f"Status: {v_status}",
                max_width=250,
            ),
        ).add_to(m)

        # Verification Neighbor Lines
        for nb in z.get("neighbors", []):
            v_match = next((x for x in verifs if x.get("zone_id") == z.get("village_id") and x.get("neighbor_id") == nb.get("id")), None)
            stat = v_match["status"] if v_match else "pending"
            folium.PolyLine(
                [[z["lat"], z["lon"]], [nb["lat"], nb["lon"]]],
                color="#7b1fa2",
                weight=2,
                dash_array="6",
                opacity=0.75,
            ).add_to(m)
            folium.Marker(
                [nb["lat"], nb["lon"]],
                icon=folium.Icon(color=NEIGHBOR_COLOR.get(stat, "blue"), icon="phone", prefix="fa"),
                tooltip=f"Verification Node: {nb['name']} ({nb.get('distance_km', '-')} km) — {stat}",
            ).add_to(m)

    # 5. Flooded Villages with Active SOS
    for v in results.get("flooded_sos", []):
        folium.CircleMarker(
            [v["lat"], v["lon"]],
            radius=7,
            color="#e65100",
            fill=True,
            fill_color="#ff9800",
            fill_opacity=0.9,
            tooltip=f"🟧 Flooded (SOS active): {v['name']} ({v['sos_count']} SOS)",
            popup=folium.Popup(f"<b>🟧 {html.escape(v['name'])}</b><br/>Status: Flooded (SOS active: {v['sos_count']})<br/>Pop: ~{v['population']}", max_width=240),
        ).add_to(m)

    # 6. Safe / Dry Villages in Radius
    for s in results.get("safe_zones", []):
        folium.CircleMarker(
            [s["lat"], s["lon"]],
            radius=6,
            color="#1b5e20",
            fill=True,
            fill_color="#4caf50",
            fill_opacity=0.9,
            tooltip=f"🟩 Safe Settlement: {s['name']} (Pop: ~{s['population']})",
            popup=folium.Popup(f"<b>🟩 {html.escape(s['name'])}</b><br/>Status: Safe / Dry Buffer<br/>Pop: ~{s['population']}", max_width=240),
        ).add_to(m)

    # 7. Multi-Agent Dispatch Routes & Bases
    if dispatch and dispatch.get("assignments"):
        for a in dispatch["assignments"]:
            for role, color in (("primary", "#d81b60"), ("secondary", "#00897b")):
                u = a.get(role)
                if not u:
                    continue
                folium.PolyLine(
                    u["route"],
                    color=color,
                    weight=4 if role == "primary" else 3,
                    opacity=0.85,
                    dash_array=None if role == "primary" else "8",
                    tooltip=f"{u['agent']} ➔ {a['zone_name']} ({role}, ETA {u['eta_min']} min)",
                ).add_to(m)
                folium.Marker(
                    [u["base"]["lat"], u["base"]["lon"]],
                    icon=folium.Icon(color="purple", icon="plus-square", prefix="fa"),
                    tooltip=f"Agency Base: {u['agent']}",
                ).add_to(m)

    return m


# ------------------------------------------------------------------ Main Screen Header
st.title("🛡️ The SilentZone Sentinel")
st.caption("خاموش زون سینٹینیل — Centralized Multi-Agent Geospatial Flood Intelligence & Silent Zone Radar")

scen_data = call("GET", "/api/scenario")
if not scen_data:
    st.error(f"Cannot connect to backend scenario data at {API}. Please ensure FastAPI backend is running.")
    st.stop()

# Prepare Selection List: Pakistan Cities + Local Villages
villages = scen_data.get("villages", [])
city_options = []
for c in sorted(PAKISTAN_CITIES, key=lambda x: (x["province"], x["name"])):
    city_options.append({
        "label": f"🇵🇰 {c['name']} ({c['province']})",
        "name": c["name"],
        "province": c["province"],
        "lat": c["lat"],
        "lon": c["lon"],
        "type": "city",
    })

for v in villages:
    status_tag = "🌊 Flooded" if v.get("in_flood") else "🌱 Dry"
    city_options.append({
        "label": f"🏡 {v['name']} [{status_tag} - Pop: {v['population']}]",
        "name": v["name"],
        "province": v.get("district", "Punjab"),
        "lat": v["lat"],
        "lon": v["lon"],
        "type": "settlement",
    })


# ------------------------------------------------------------------ Top Control Panel: Area & Radius Configuration
with st.container(border=True):
    st.markdown("### ⚙️ Scan Target & Radius Configuration")
    
    col_mode, col_rad = st.columns([2, 1])
    with col_mode:
        loc_mode = st.radio(
            "Location Selector Mode:",
            ["Choose Pakistan City / District / Settlement", "Custom GPS Coordinates (Lat/Lon)"],
            horizontal=True,
            key="cfg_loc_mode",
        )
    with col_rad:
        scan_radius = st.slider("Scan Radius (10 — 100 KM):", min_value=10, max_value=100, value=30, step=1, key="cfg_scan_radius")

    c_lat, c_lon, c_name = 29.1035, 70.3250, "Rajanpur"

    if loc_mode == "Choose Pakistan City / District / Settlement":
        default_idx = next((i for i, item in enumerate(city_options) if item["name"] == "Rajanpur"), 0)
        selected_item = st.selectbox(
            "Select Target City / District / Local Settlement:",
            city_options,
            format_func=lambda x: x["label"],
            index=default_idx,
            key="cfg_city_select",
        )
        if selected_item:
            c_lat = selected_item["lat"]
            c_lon = selected_item["lon"]
            c_name = selected_item["name"]
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            c_lat = st.number_input("Latitude (°N):", value=29.1035, format="%.4f", step=0.01, key="cfg_num_lat")
        with c2:
            c_lon = st.number_input("Longitude (°E):", value=70.3250, format="%.4f", step=0.01, key="cfg_num_lon")
        with c3:
            c_name = st.text_input("Sector Label / Name:", value="Custom Target Sector", key="cfg_txt_sector")

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    
    # Primary Action Process Button
    process_clicked = st.button("🚀 Process Flood Analysis & Launch Sentinel Multi-Agent Pipeline", type="primary", use_container_width=True, key="btn_main_process")

# Handle Process Click
if process_clicked:
    with st.spinner(f"🔍 Analyzing flood coverage, detecting silent zones, and executing multi-agent pipeline for {c_name} ({scan_radius} KM)..."):
        # 1. Geospatial Analysis
        results = scan_area_and_radius(c_lat, c_lon, scan_radius, scen_data)
        summary = results["summary"]
        
        # 2. Trigger Multi-Agent Pipeline Backend
        run_res = call("POST", "/api/runs")
        run_id = run_res["run_id"] if run_res else None
        st.session_state["run_id"] = run_id
        
        # 3. Save Scan into SQLite Database
        username = user.get("username", "operator")
        operator_name = user.get("name", "Active Operator")
        db.save_scan_report(
            username=username,
            operator_name=operator_name,
            area_name=c_name,
            lat=c_lat,
            lon=c_lon,
            radius_km=scan_radius,
            summary=summary,
            details=results,
        )
        
        # 4. Save into Session State
        st.session_state["has_processed"] = True
        st.session_state["active_scan"] = {
            "results": results,
            "summary": summary,
            "c_lat": c_lat,
            "c_lon": c_lon,
            "c_name": c_name,
            "radius_km": scan_radius,
        }
        st.toast(f"Flood analysis & Multi-Agent pipeline launched for {c_name} ({scan_radius} KM)!", icon="🚀")


# ------------------------------------------------------------------ Display View Logic
has_processed = st.session_state.get("has_processed", False)
active_scan = st.session_state.get("active_scan")

if not has_processed or not active_scan:
    # Clean Initial State (Map is NOT loaded until user selects and clicks Process)
    st.info(
        "💡 **Ready to Initialize System**: Select a Pakistan City/District or Settlement and desired scan radius (10–100 KM) above, "
        "then click **'🚀 Process Flood Analysis & Launch Sentinel Multi-Agent Pipeline'** to generate the unified interactive map, "
        "detect cut-off silent zones, execute agent verifications, and formulate rescue dispatches."
    )
    
    # Historical preview card before scan
    with st.container(border=True):
        st.subheader("📚 Recent Saved Scan Reports in Database")
        past_reports = db.get_all_reports(limit=5)
        if past_reports:
            p_rows = []
            for r in past_reports:
                p_rows.append({
                    "Report ID": f"REP-{r['id']:04d}",
                    "Date": r["created_at"],
                    "Operator": r["operator_name"],
                    "Target Area": r["area_name"],
                    "Radius": f"{r['radius_km']} km",
                    "Flooded": r["total_flooded"],
                    "Silent Zones": r["total_silent"],
                    "Pop at Risk": f"{r['total_pop_affected']:,}",
                })
            st.dataframe(pd.DataFrame(p_rows), hide_index=True, use_container_width=True)
        else:
            st.caption("No historical scans saved in database yet. Process your first scan above.")
else:
    # ------------------------------------------------------------------ Single Unified Post-Processing Dashboard
    results = active_scan["results"]
    summary = active_scan["summary"]
    c_lat = active_scan["c_lat"]
    c_lon = active_scan["c_lon"]
    c_name = active_scan["c_name"]
    scan_radius = active_scan["radius_km"]

    rid = st.session_state.get("run_id")
    current_run = call("GET", f"/api/runs/{rid}") if rid else None
    secs = (current_run or {}).get("sections", {})
    agent_zones = secs.get("silent_zones", [])
    verifs = secs.get("verifications", [])
    bids = secs.get("bids", [])
    weather_info = secs.get("weather")

    # If backend agent pipeline identified additional silent zones with neighbor graph, merge them
    if agent_zones:
        # Match neighbors to results silent zones
        for az in agent_zones:
            for sz in results["silent_zones"]:
                if sz.get("village_id") == az.get("village_id") or sz.get("name") == az.get("name"):
                    sz["neighbors"] = az.get("neighbors", [])
                    sz["verification"] = az.get("verification", {})

    st.markdown("---")

    # 1. Top Centralized Metric Bar
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Pipeline Status", (current_run or {}).get("status", "completed").upper())
    m2.metric("Settlements in Radius", summary["total_villages"])
    m3.metric("🚨 SILENT ZONES", summary["total_silent"], delta=f"{summary['silent_pop']:,} at risk" if summary['total_silent'] else "Clear", delta_color="inverse")
    m4.metric("Neighbor Replies", f"{sum(v['status'] not in ('pending',) for v in verifs)}/{len(verifs)}" if verifs else "N/A")
    m5.metric("Agency Bids", len(bids))
    m6.metric("Flood Severity", weather_info["level"] if weather_info else "Moderate", help=f"Rain: {weather_info['rain_past_3d_mm']} mm / 3d" if weather_info else None)

    # 2. Main Two-Column Layout: Single Unified Map on Left + Centralized Multi-Agent Panels on Right
    map_col, panel_col = st.columns([3, 2])

    with map_col:
        st.subheader(f"🗺️ Unified Spatial Map ({c_name} · {scan_radius} KM Radius)")
        unified_map = build_unified_map(c_lat, c_lon, scan_radius, c_name, scen_data, current_run, results)
        st_folium(unified_map, height=580, use_container_width=True, returned_objects=[], key="single_unified_map")
        st.caption(
            "🔵 Target Center · 🔴 Radius Circle · 🟥 Silent Zone (0 SOS) · 🟧 Flooded with SOS · 🟩 Dry Settlement · "
            "🟣 Dashed Vector: Neighbor Check · 🌸/🩵 Solid Lines: Rescue Routes"
        )

    with panel_col:
        st.subheader("📋 Centralized Intelligence & Agent Operations")

        tab_impact, tab_log, tab_ver, tab_bid, tab_disp, tab_tg, tab_hist = st.tabs([
            "📊 Sector Impact",
            "🤖 Agent Logs",
            "📞 Verification",
            "🏷️ Bids",
            "📜 Approval",
            "📱 Telegram",
            "📚 DB History",
        ])

        # TAB 1: Sector Impact & PDF Download
        with tab_impact:
            st.markdown(f"**Target Sector:** `{c_name}` ({c_lat:.4f}°N, {c_lon:.4f}°E) · **Radius:** `{scan_radius} KM`")
            
            sub_silent, sub_sos, sub_safe = st.tabs([
                f"🟥 Silent ({len(results['silent_zones'])})",
                f"🟧 Flooded SOS ({len(results['flooded_sos'])})",
                f"🟩 Safe Buffer ({len(results['safe_zones'])})",
            ])

            with sub_silent:
                if results["silent_zones"]:
                    st.markdown("<p style='color: #d32f2f; font-weight: 600;'>🚨 Inundated villages with ZERO calls (High Risk).</p>", unsafe_allow_html=True)
                    df_silent = pd.DataFrame([{
                        "Zone": z["name"],
                        "Distance": f"{z['distance_km']} km",
                        "Pop": z["population"],
                        "Depth": f"{z['flood_depth_m']} m",
                        "SOS": "0 (SILENT)",
                    } for z in results["silent_zones"]])
                    st.dataframe(df_silent, hide_index=True, use_container_width=True)
                else:
                    st.success("No silent zones found in this radius.")

            with sub_sos:
                if results["flooded_sos"]:
                    df_sos = pd.DataFrame([{
                        "Village": v["name"],
                        "Distance": f"{v['distance_km']} km",
                        "Pop": v["population"],
                        "SOS Active": v.get("sos_count", 0),
                    } for v in results["flooded_sos"]])
                    st.dataframe(df_sos, hide_index=True, use_container_width=True)
                else:
                    st.info("No flooded settlements with active SOS in this radius.")

            with sub_safe:
                if results["safe_zones"]:
                    df_safe = pd.DataFrame([{
                        "Village": s["name"],
                        "Distance": f"{s['distance_km']} km",
                        "Pop": s["population"],
                        "Rep": s.get("rep", "Representative"),
                    } for s in results["safe_zones"]])
                    st.dataframe(df_safe, hide_index=True, use_container_width=True)
                else:
                    st.warning("No dry buffer villages in this radius.")

            # PDF Download Button
            st.markdown("---")
            with st.container(border=True):
                st.markdown("#### 📄 Export Official Assessment Report")
                st.caption("Generate an authoritative PDF document with executive summary, maps data, and operational breakdown.")
                
                operator_name = user.get("name", "Active Operator")
                pdf_data = generate_area_flood_pdf(
                    area_name=c_name,
                    lat=c_lat,
                    lon=c_lon,
                    radius_km=float(scan_radius),
                    summary=summary,
                    silent_zones=results["silent_zones"],
                    flooded_sos=results["flooded_sos"],
                    safe_zones=results["safe_zones"],
                    weather_info=weather_info,
                    operator_name=operator_name,
                )
                
                pdf_filename = f"SilentZone_Sentinel_{c_name.replace(' ', '_')}_{scan_radius}KM.pdf"
                st.download_button(
                    label="📥 Download Flood Assessment PDF Report",
                    data=pdf_data,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key="btn_download_unified_pdf",
                )

        # TAB 2: Live Agent Logs
        with tab_log:
            log_box = st.container(height=450)
            logs = (current_run or {}).get("logs", [])
            if not logs:
                log_box.info("No agent logs available yet.")
            for l in logs[-250:]:
                icon = AGENT_BADGE.get(l.get("agent"), "🟨")
                log_box.markdown(f"`{l.get('t', '')}` {icon} **{l.get('agent', 'System')}** — {l.get('message', '')}")

        # TAB 3: Neighbor Verification
        with tab_ver:
            if not verifs:
                st.caption("No neighbor verification inquiries in progress.")
            for v in verifs:
                with st.container(border=True):
                    st.markdown(f"**{v.get('neighbor_name', 'Neighbor')}** ➔ *{v.get('zone_name', 'Zone')}* ({v.get('distance_km', '-')} km) — `{v.get('status')}`")
                    st.caption(v.get("question", ""))
                    if v.get("status") == "pending":
                        c1, c2, c3 = st.columns(3)
                        for col, ans, label in ((c1, "yes", "Yes, cut off"), (c2, "no", "No flooding"), (c3, "unsure", "Not sure")):
                            if col.button(label, key=f"ver-{v.get('id')}-{ans}"):
                                call("POST", f"/api/runs/{rid}/verification", json={"vid": v.get("id"), "answer": ans})
                                st.rerun()

        # TAB 4: Resource Agency Bids
        with tab_bid:
            if not bids:
                st.caption("Waiting for agency bids (Rescue 1122, Edhi, Al-Khidmat)...")
            else:
                df_bids = pd.DataFrame([{k: b.get(k) for k in ("zone_id", "agent", "eta_min", "distance_km", "resource_match",
                                                               "fuel_score", "feasibility", "declined")} for b in bids])
                st.dataframe(df_bids, hide_index=True, use_container_width=True)
                with st.expander("🔍 View Raw JSON Bids"):
                    st.json([{k: v for k, v in b.items() if k != "route"} for b in bids])

        # TAB 5: Coordinator Approval
        with tab_disp:
            disp = (current_run or {}).get("dispatch")
            if not disp:
                st.caption("Waiting for Coordinator AI recommendation...")
            else:
                with st.container(border=True):
                    st.subheader(f"Dispatch Plan: {disp.get('id', 'REC-01')}")
                    st.markdown(f"**Status:** `{disp.get('status', 'pending')}` · Evaluator: `{disp.get('explanation_source', 'LangGraph')}`")
                    st.markdown(disp.get("english", ""))
                    
                    if disp.get("urdu"):
                        st.markdown(
                            f"<div dir='rtl' style='font-size:1.1rem;line-height:1.9;background:#f8fafc;padding:12px;border-radius:8px;border-right:4px solid #0284c7;'>"
                            + html.escape(disp["urdu"]).replace("\n", "<br>") + "</div>",
                            unsafe_allow_html=True,
                        )
                    
                    if disp.get("assignments"):
                        st.markdown("#### 🎯 Resource Allocations")
                        st.dataframe(
                            pd.DataFrame([{
                                "Zone": a.get("zone_name"),
                                "Pop": a.get("population"),
                                "Primary": f"{a.get('primary', {}).get('agent', '-')} ({a.get('primary', {}).get('eta_min', '-')} min)",
                                "Support": (f"{a.get('secondary', {}).get('agent', '-')} ({a.get('secondary', {}).get('eta_min', '-')} min)" if a.get("secondary") else "-"),
                            } for a in disp["assignments"]]),
                            hide_index=True,
                            use_container_width=True,
                        )

                    if disp.get("status") == "pending":
                        b1, b2 = st.columns(2)
                        if b1.button("✅ Approve Dispatch Orders", type="primary", use_container_width=True, key=f"btn_app_{rid}"):
                            call("POST", f"/api/runs/{rid}/approve")
                            st.rerun()
                        if b2.button("❌ Reject Dispatch", use_container_width=True, key=f"btn_rej_{rid}"):
                            call("POST", f"/api/runs/{rid}/reject")
                            st.rerun()
                    elif disp.get("status") == "approved":
                        st.success("✅ Orders Approved — Rescue units dispatched across field channels.")
                    elif disp.get("status") == "rejected":
                        st.error("❌ Orders Rejected by Coordinator.")

        # TAB 6: Telegram Outbox
        with tab_tg:
            outbox = call("GET", "/api/outbox") or []
            if rid:
                outbox = [o for o in outbox if o.get("run_id") in (rid, None)]
            if not outbox:
                st.caption("No dispatched telegram alerts yet.")
            for o in reversed(outbox):
                with st.container(border=True):
                    st.caption(f"🕒 {o.get('t', '')} · {o.get('channel', 'TG')} ➔ {o.get('to', '')} · `{o.get('delivered', 'sent')}`")
                    st.text(o.get("text", "")[:700])
                    if o.get("buttons"):
                        st.caption("Buttons: " + " | ".join(o.get("buttons", [])))

        # TAB 7: Database Scan History
        with tab_hist:
            st.markdown("#### 📚 Stored SQLite Reports")
            all_reports = db.get_all_reports(limit=25)
            if all_reports:
                hist_data = []
                for rep in all_reports:
                    hist_data.append({
                        "ID": f"REP-{rep['id']:04d}",
                        "Timestamp": rep["created_at"],
                        "Operator": rep["operator_name"],
                        "Area": rep["area_name"],
                        "Radius": f"{rep['radius_km']} km",
                        "Flooded": rep["total_flooded"],
                        "Silent": rep["total_silent"],
                        "Pop Affected": f"{rep['total_pop_affected']:,}",
                    })
                st.dataframe(pd.DataFrame(hist_data), hide_index=True, use_container_width=True)
            else:
                st.info("No scan reports found in SQLite database.")