"""Area and Radius Flood Scanner with Geospatial Filtering across all Pakistan cities and PDF Report Generation.
Scanning only runs when the user explicitly clicks the Process button. All scans are recorded in SQLite.
"""
import html
import math
import sys
from pathlib import Path
import folium
import pandas as pd
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
    from frontend.pakistan_cities import PAKISTAN_CITIES
    from frontend.pdf_report import generate_area_flood_pdf
except ImportError:
    from pakistan_cities import PAKISTAN_CITIES
    from pdf_report import generate_area_flood_pdf


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


def build_radius_map(center_lat: float, center_lon: float, radius_km: float, scen: dict, results: dict, center_label: str) -> folium.Map:
    zoom = 11 if radius_km <= 20 else 10 if radius_km <= 45 else 9 if radius_km <= 75 else 8
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")
    
    # 1. Flood polygon layer
    def style(f):
        deep = f["properties"].get("depth_m", 1) >= 2
        return {"color": "#08306b" if deep else "#2171b5", "weight": 2,
                "fillColor": "#08519c" if deep else "#6baed6", "fillOpacity": 0.40 if deep else 0.25}
                
    folium.GeoJson(scen["flood"], name="Flood Footprint", style_function=style,
                   tooltip=folium.GeoJsonTooltip(fields=["name", "depth_m"], aliases=["Flood Zone", "Depth (m)"])).add_to(m)
                   
    # 2. Search Radius Circle
    folium.Circle(
        location=[center_lat, center_lon],
        radius=radius_km * 1000,
        color="#d32f2f",
        weight=2.5,
        fill=True,
        fill_color="#ffcdd2",
        fill_opacity=0.18,
        tooltip=f"Scan Radius: {radius_km} KM around {center_label}",
    ).add_to(m)
    
    # 3. Center Anchor Marker
    folium.Marker(
        [center_lat, center_lon],
        icon=folium.Icon(color="darkblue", icon="map-marker", prefix="fa"),
        tooltip=f"Target: {center_label} ({center_lat:.4f}°N, {center_lon:.4f}°E) · Radius {radius_km} km",
        popup=folium.Popup(f"<b>📍 Selected Center: {html.escape(center_label)}</b><br/>Radius: {radius_km} KM", max_width=240),
    ).add_to(m)
    
    # 4. Silent Zones Markers
    for z in results["silent_zones"]:
        folium.Marker(
            [z["lat"], z["lon"]],
            icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"),
            tooltip=f"🟥 SILENT ZONE: {z['name']} ({z['distance_km']} km away)",
            popup=folium.Popup(
                f"<b>🟥 SILENT ZONE: {html.escape(z['name'])}</b><br/>"
                f"Distance: {z['distance_km']} km<br/>"
                f"Population: ~{z['population']}<br/>"
                f"Flood Depth: {z['flood_depth_m']} m<br/>"
                f"<b>SOS Count: 0 (Cut-off)</b>",
                max_width=250,
            ),
        ).add_to(m)
        
    # 5. Flooded with SOS Markers
    for v in results["flooded_sos"]:
        folium.CircleMarker(
            [v["lat"], v["lon"]],
            radius=7,
            color="#e65100",
            fill=True,
            fill_color="#ff9800",
            fill_opacity=0.9,
            tooltip=f"🟧 Flooded (SOS active): {v['name']} ({v['sos_count']} SOS, {v['distance_km']} km away)",
            popup=folium.Popup(
                f"<b>🟧 {html.escape(v['name'])}</b><br/>"
                f"Status: Flooded (SOS Active)<br/>"
                f"Distance: {v['distance_km']} km<br/>"
                f"Population: ~{v['population']}<br/>"
                f"SOS Signals: {v['sos_count']}",
                max_width=240,
            ),
        ).add_to(m)
        
    # 6. Dry / Safe Markers
    for s in results["safe_zones"]:
        folium.CircleMarker(
            [s["lat"], s["lon"]],
            radius=6,
            color="#1b5e20",
            fill=True,
            fill_color="#4caf50",
            fill_opacity=0.9,
            tooltip=f"🟩 Safe / Dry: {s['name']} ({s['distance_km']} km away)",
            popup=folium.Popup(
                f"<b>🟩 {html.escape(s['name'])}</b><br/>"
                f"Status: Safe / Dry Settlement<br/>"
                f"Distance: {s['distance_km']} km<br/>"
                f"Population: ~{s['population']}<br/>"
                f"Rep: {html.escape(s.get('rep', 'Village Rep'))}",
                max_width=240,
            ),
        ).add_to(m)
        
    return m


def render_area_scanner(scen: dict, weather_info: dict | None, user: dict):
    """Renders the Area & Radius Flood Scanner. Processing only executes on explicit user trigger."""
    st.header("📍 Pakistan Area & Radius Flood Scanner")
    st.caption("Configure target area and scan radius. Click the Process button to run flood assessment, detect silent zones, and generate an official PDF report.")
    
    villages = scen.get("villages", [])
    
    # Combined selection list: Pakistan Cities & Local Settlements
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
        
    # Tab views for New Scan vs Database History
    scan_tab, history_tab = st.tabs(["🎯 New Area Flood Scan", "📚 Stored Database Scan History"])

    with scan_tab:
        # Form Container for Selection so it NEVER triggers automatically
        with st.container(border=True):
            st.markdown("### ⚙️ Scan Parameters & Selection")
            
            col_mode, col_rad = st.columns([2, 1])
            with col_mode:
                loc_mode = st.radio(
                    "Location Mode:",
                    ["Choose Pakistan City / District / Settlement", "Custom GPS Coordinates (Lat/Lon)"],
                    horizontal=True,
                    key="scanner_loc_mode"
                )
            with col_rad:
                scan_radius = st.slider("Scan Radius (10 - 100 KM):", min_value=10, max_value=100, value=25, step=1, key="scan_rad_slider")

            c_lat, c_lon, c_name = 29.1035, 70.3250, "Rajanpur"

            if loc_mode == "Choose Pakistan City / District / Settlement":
                default_idx = next((i for i, item in enumerate(city_options) if item["name"] == "Rajanpur"), 0)
                selected_item = st.selectbox(
                    "Select Target Pakistan City / District:",
                    city_options,
                    format_func=lambda x: x["label"],
                    index=default_idx,
                    key="scanner_city_select"
                )
                if selected_item:
                    c_lat = selected_item["lat"]
                    c_lon = selected_item["lon"]
                    c_name = selected_item["name"]
            else:
                c1, c2, c3 = st.columns(3)
                with c1:
                    c_lat = st.number_input("Latitude:", value=29.1035, format="%.4f", step=0.01, key="num_lat")
                with c2:
                    c_lon = st.number_input("Longitude:", value=70.3250, format="%.4f", step=0.01, key="num_lon")
                with c3:
                    c_name = st.text_input("Sector Name / Label:", value="Custom Sector", key="txt_sector_name")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            
            # Explicit Process Button
            process_btn = st.button("🚀 Process & Scan Selected Area", type="primary", use_container_width=True, key="btn_run_scan")

        # Process when user explicitly clicks the button
        if process_btn:
            with st.spinner(f"🔍 Analyzing flood coverage, settlement proximity, and silent zones for {c_name} ({scan_radius} KM)..."):
                results = scan_area_and_radius(c_lat, c_lon, scan_radius, scen)
                summary = results["summary"]
                
                # Save scan record to SQLite database
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
                
                # Save into session state so it stays visible
                st.session_state["active_scan_data"] = {
                    "results": results,
                    "summary": summary,
                    "c_lat": c_lat,
                    "c_lon": c_lon,
                    "c_name": c_name,
                    "radius_km": scan_radius,
                }
                st.success(f"✅ Scan completed for **{c_name}** ({scan_radius} KM radius) and recorded in database!")

        # Render active scan results if available
        active_scan = st.session_state.get("active_scan_data")

        if active_scan:
            results = active_scan["results"]
            summary = active_scan["summary"]
            c_lat = active_scan["c_lat"]
            c_lon = active_scan["c_lon"]
            c_name = active_scan["c_name"]
            scan_radius = active_scan["radius_km"]

            st.markdown("---")
            
            # Metric Summary Row
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Settlements in Radius", summary["total_villages"])
            m2.metric("Flooded Settlements", summary["total_flooded"], delta=f"{summary['total_flooded']} affected" if summary['total_flooded'] else None, delta_color="inverse")
            m3.metric("🚨 SILENT ZONES (0 SOS)", summary["total_silent"], delta="Critical Priority" if summary['total_silent'] else "Clear", delta_color="inverse")
            m4.metric("Population at Risk", f"{summary['total_pop_affected']:,}")
            m5.metric("Safe Buffer Villages", summary["total_safe"])
            
            # Interactive Map & Data Views
            map_col, data_col = st.columns([3, 2])
            
            with map_col:
                st.subheader(f"🗺️ Spatial Assessment ({c_name} · {scan_radius} KM Radius)")
                rad_map = build_radius_map(c_lat, c_lon, scan_radius, scen, results, c_name)
                st_folium(rad_map, height=530, use_container_width=True, returned_objects=[], key="active_radius_map")
                st.caption("🔵 Blue Marker: Selected Pakistan City / Center · 🔴 Red Circle: Radius Boundary · 🟥 Red Markers: Silent Zones · 🟧 Orange: Flooded with SOS · 🟩 Green: Dry Buffer")
                
            with data_col:
                st.subheader("📋 Sector Breakdown")
                
                tab_silent, tab_flooded, tab_safe = st.tabs([
                    f"🟥 Silent Zones ({len(results['silent_zones'])})",
                    f"🟧 Flooded with SOS ({len(results['flooded_sos'])})",
                    f"🟩 Safe Buffer ({len(results['safe_zones'])})",
                ])
                
                with tab_silent:
                    if results["silent_zones"]:
                        st.markdown("<p style='color: #d32f2f; font-weight: bold;'>🚨 Critical: Inundated settlements with zero SOS signals.</p>", unsafe_allow_html=True)
                        df_silent = pd.DataFrame([{
                            "Zone": z["name"],
                            "Distance": f"{z['distance_km']} km",
                            "Pop": z["population"],
                            "Depth": f"{z['flood_depth_m']} m",
                            "SOS": "0 (SILENT)",
                        } for z in results["silent_zones"]])
                        st.dataframe(df_silent, hide_index=True, use_container_width=True)
                    else:
                        st.success("No silent zones found within this radius.")
                        
                with tab_flooded:
                    if results["flooded_sos"]:
                        df_sos = pd.DataFrame([{
                            "Settlement": v["name"],
                            "Distance": f"{v['distance_km']} km",
                            "Pop": v["population"],
                            "Depth": f"{v.get('flood_depth_m', 1.0)} m",
                            "SOS Active": v.get("sos_count", 0),
                        } for v in results["flooded_sos"]])
                        st.dataframe(df_sos, hide_index=True, use_container_width=True)
                    else:
                        st.info("No flooded settlements with active SOS signals in this radius.")
                        
                with tab_safe:
                    if results["safe_zones"]:
                        df_safe = pd.DataFrame([{
                            "Settlement": s["name"],
                            "Distance": f"{s['distance_km']} km",
                            "Pop": s["population"],
                            "Representative": s.get("rep", "Representative"),
                        } for s in results["safe_zones"]])
                        st.dataframe(df_safe, hide_index=True, use_container_width=True)
                    else:
                        st.warning("No dry buffer settlements inside this radius.")
                        
                # PDF Generation & Download Action Box
                st.markdown("---")
                with st.container(border=True):
                    st.markdown("### 📄 Export Official Assessment Report")
                    st.caption("Generate a formatted PDF report with comprehensive statistics, village breakdown, and operational recommendations.")
                    
                    operator_name = user.get("name", "Active Operator")
                    pdf_bytes = generate_area_flood_pdf(
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
                    
                    file_name = f"SilentZone_Sentinel_Report_{c_name.replace(' ', '_')}_{scan_radius}KM.pdf"
                    st.download_button(
                        label="📥 Download Flood Assessment Report (PDF)",
                        data=pdf_bytes,
                        file_name=file_name,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                        key="btn_download_pdf"
                    )
                    st.caption("Prepared by: **Malik Junaid Ahmad** & **Saira Khan**")
        else:
            # Idle placeholder when no scan has been executed yet
            st.info("💡 **Ready to Scan**: Select a Pakistan City / District and desired radius in KM above, then click **'🚀 Process & Scan Selected Area'** to run the spatial assessment.")

    # 2. Database History Tab
    with history_tab:
        st.subheader("📚 Saved Flood Assessment Reports in SQLite Database")
        st.caption("All previously executed area scans are recorded in the database history.")

        past_reports = db.get_all_reports(limit=30)
        if past_reports:
            history_rows = []
            for r in past_reports:
                history_rows.append({
                    "Report ID": f"REP-{r['id']:04d}",
                    "Date & Time": r["created_at"],
                    "Operator": r["operator_name"],
                    "Target Area": r["area_name"],
                    "Radius (KM)": f"{r['radius_km']} km",
                    "Flooded": r["total_flooded"],
                    "Silent Zones": r["total_silent"],
                    "Pop at Risk": f"{r['total_pop_affected']:,}",
                })
            st.dataframe(pd.DataFrame(history_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No scan reports recorded in the database yet. Process an area scan above to save the first report.")
