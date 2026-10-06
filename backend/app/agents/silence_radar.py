"""Agent 1 - Silence Radar: flooded villages with zero SOS requests become 'Silent Zones'."""
import httpx

from .. import data_loader, store
from ..services import geo
from ..services import weather as weather_svc

AGENT = "Silence Radar"


async def silence_radar_node(state: dict) -> dict:
    rid = state["run_id"]
    flood = data_loader.load_flood()
    villages = data_loader.load_villages()
    sos = data_loader.load_sos()
    shapes = geo.build_flood_shapes(flood)
    store.log(rid, AGENT, f"Loaded {len(shapes)} flood polygon(s), {len(villages)} settlements, {len(sos)} SOS requests.")

    lat, lon = geo.flood_centroid(shapes)
    async with httpx.AsyncClient() as client:
        w = await weather_svc.fetch_weather(client, lat, lon)
    sev = weather_svc.severity_from_weather(w)
    store.log(rid, AGENT,
              f"Open-Meteo ({w['source']}): {w['rain_past_3d_mm']} mm in past 3 days, "
              f"{w['rain_forecast_mm']} mm forecast, soil saturation {int(w['soil_saturation'] * 100)}% "
              f"-> severity {sev['level']} (index {sev['index']}).")
    store.set_section(rid, "weather", {**w, **sev})

    counts = data_loader.sos_counts(villages, sos)
    flooded, zones = [], []
    for v in villages:
        info = geo.point_flood_info(v["lat"], v["lon"], shapes)
        if not info:
            continue
        flooded.append(v["id"])
        if counts.get(v["id"], 0) == 0:
            zones.append({
                "village_id": v["id"], "name": v["name"], "lat": v["lat"], "lon": v["lon"],
                "population": v["population"], "district": v.get("district", ""),
                "flood_depth_m": info["depth_m"], "flood_polygon": info["polygon"],
                "sos_count": 0, "verification": {"status": "PENDING"},
            })
    zones.sort(key=lambda z: -z["population"])
    for i, z in enumerate(zones, start=1):
        z["id"] = f"Z{i}"

    store.log(rid, AGENT, f"{len(flooded)} settlements lie inside flood water; "
                          f"{len(flooded) - len(zones)} have sent SOS, {len(zones)} are SILENT.",
              "warn" if zones else "success")
    for z in zones:
        store.log(rid, AGENT, f"SILENT ZONE {z['id']}: {z['name']} - ~{z['population']} people, "
                              f"depth ~{z['flood_depth_m']} m, 0 SOS received.", "warn")
    store.set_section(rid, "silent_zones", zones)
    store.set_section(rid, "flooded_village_ids", flooded)
    return {"weather": {**w, **sev}, "severity": sev, "silent_zones": zones}
