"""Agent 3 - Negotiating Resource Agents: Rescue 1122, Edhi Foundation and Al-Khidmat each submit a JSON bid.

Base locations are ILLUSTRATIVE (not real depots) - replace with real coordinates for production use.
"""
import asyncio

import httpx

from .. import store
from ..services import geo

AGENT = "Resource Agents"

FLEET = [
    {"id": "rescue1122", "name": "Rescue 1122",
     "base": {"name": "Rescue 1122 District Control (Rajanpur)", "lat": 29.24, "lon": 70.31},
     "assets": ["Rescue boats x6", "Ambulances x4", "Paramedic teams"],
     "speed_kmh": 55, "prep_min": 10, "fuel_pct": 0.80, "teams": 2, "daily_capacity": 600,
     "capabilities": {"boats": 0.90, "medical": 0.95, "food": 0.20, "deep_water": 0.60, "manpower": 0.60},
     "tagline": "Boats, high medical capacity, fast"},
    {"id": "edhi", "name": "Edhi Foundation",
     "base": {"name": "Edhi Centre (Jampur)", "lat": 29.64, "lon": 70.60},
     "assets": ["Ambulances x5", "Food relief trucks x2"],
     "speed_kmh": 40, "prep_min": 20, "fuel_pct": 0.65, "teams": 2, "daily_capacity": 400,
     "capabilities": {"boats": 0.20, "medical": 0.70, "food": 0.90, "deep_water": 0.10, "manpower": 0.50},
     "tagline": "Ambulances and food relief, medium speed"},
    {"id": "alkhidmat", "name": "Al-Khidmat Foundation",
     "base": {"name": "Al-Khidmat Camp (Jampur)", "lat": 29.55, "lon": 70.45},
     "assets": ["Inflatable rafts x8", "Trained volunteers x60", "Deep-water rescue kit"],
     "speed_kmh": 35, "prep_min": 25, "fuel_pct": 0.70, "teams": 2, "daily_capacity": 700,
     "capabilities": {"boats": 0.60, "medical": 0.30, "food": 0.60, "deep_water": 0.90, "manpower": 0.90},
     "tagline": "Rafts, volunteers, deep-water access"},
]
FLEET_BY_ID = {a["id"]: a for a in FLEET}


def zone_needs(zone: dict) -> dict:
    deep = zone.get("flood_depth_m", 1.0) >= 2.0
    w = {"boats": 0.30, "medical": 0.15 + min(0.15, zone["population"] / 20000.0), "food": 0.20,
         "deep_water": 0.25 if deep else 0.05, "manpower": 0.10}
    s = sum(w.values())
    return {k: round(v / s, 3) for k, v in w.items()}


async def make_bid(client: httpx.AsyncClient, agent: dict, zone: dict) -> dict:
    base = agent["base"]
    route = await geo.osrm_route(client, (base["lat"], base["lon"]), (zone["lat"], zone["lon"]))
    caps, needs = agent["capabilities"], zone_needs(zone)
    match = sum(needs[k] * caps[k] for k in needs)
    road_min = route["duration_min"] * (50.0 / agent["speed_kmh"])
    water_min = 12 + 8 * zone["flood_depth_m"] * (1 - 0.6 * max(caps["boats"], caps["deep_water"]))
    eta = agent["prep_min"] + road_min + water_min
    eta_score = max(0.0, 1 - eta / 240.0)
    need_km = 2 * route["distance_km"] * 1.15
    fuel_score = min(1.0, agent["fuel_pct"] * 350.0 / need_km) if need_km > 0 else 1.0
    cap_score = min(1.0, agent["daily_capacity"] / (0.3 * zone["population"]))
    feas = 0.40 * match + 0.30 * eta_score + 0.20 * fuel_score + 0.10 * cap_score
    declined, reason = False, ""
    if agent["teams"] <= 0:
        declined, reason = True, "no team available"
    elif fuel_score < 0.5:
        declined, reason = True, "insufficient fuel for round trip"
    return {
        "bid_id": f"B-{zone['id']}-{agent['id']}", "zone_id": zone["id"], "agent_id": agent["id"],
        "agent": agent["name"], "base": base, "assets_offered": agent["assets"],
        "distance_km": round(route["distance_km"], 1), "road_eta_min": round(road_min),
        "prep_min": agent["prep_min"], "water_leg_min": round(water_min), "eta_min": round(eta),
        "resource_match": round(match, 2), "fuel_score": round(fuel_score, 2),
        "capacity_score": round(cap_score, 2), "feasibility": round(feas, 2),
        "teams_available": agent["teams"], "declined": declined, "decline_reason": reason,
        "route": route["geometry"], "route_source": route["source"], "complements": [],
    }


async def negotiation_node(state: dict) -> dict:
    rid = state["run_id"]
    zones = [z for z in state["silent_zones"] if z["verification"]["status"] != "NOT_CONFIRMED"]
    skipped = [z for z in state["silent_zones"] if z["verification"]["status"] == "NOT_CONFIRMED"]
    for z in skipped:
        store.log(rid, AGENT, f"{z['id']} {z['name']} skipped: neighbors report no flooding.", "warn")
    bids: list[dict] = []
    store.set_section(rid, "bids", bids)
    async with httpx.AsyncClient() as client:
        for z in zones:
            store.log(rid, AGENT, f"Call for bids: {z['id']} {z['name']} (~{z['population']} people, depth {z['flood_depth_m']} m).")
            zone_bids = await asyncio.gather(*[make_bid(client, a, z) for a in FLEET])
            for b in zone_bids:
                if b["declined"]:
                    store.log(rid, b["agent"], f"DECLINES {z['name']}: {b['decline_reason']}.", "warn")
                else:
                    store.log(rid, b["agent"],
                              f"BID for {z['name']}: ETA {b['eta_min']} min ({b['distance_km']} km, {b['route_source']}), "
                              f"match {b['resource_match']}, fuel {b['fuel_score']}, feasibility {b['feasibility']}.")
            live = [b for b in zone_bids if not b["declined"]]
            if live:
                leader = max(live, key=lambda b: b["feasibility"])
                lcaps = FLEET_BY_ID[leader["agent_id"]]["capabilities"]
                for b in live:
                    if b is leader:
                        continue
                    caps = FLEET_BY_ID[b["agent_id"]]["capabilities"]
                    b["complements"] = [k for k in caps if lcaps[k] < 0.6 <= caps[k]]
                    if b["complements"]:
                        store.log(rid, b["agent"], f"Offers to complement {leader['agent']} on: {', '.join(b['complements'])}.")
            bids.extend(zone_bids)
    store.set_section(rid, "bids", bids)
    return {"bids": bids}
