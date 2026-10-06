"""Agent 2 - Neighbor Verification: ask villages just outside the flood boundary whether a silent zone is cut off."""
import asyncio
import hashlib
import random
import time

import httpx

from .. import data_loader, store
from ..config import settings
from ..services import geo, telegram

AGENT = "Neighbor Verification"


def _dedupe(cands: list[dict]) -> list[dict]:
    out: list[dict] = []
    for c in sorted(cands, key=lambda c: c["distance_km"]):
        if any(geo.haversine_km(c["lat"], c["lon"], o["lat"], o["lon"]) < 0.5 for o in out):
            continue
        out.append(c)
    return out


async def _auto_reply(run_id: str, vid: str, answer: str, delay: float) -> None:
    await asyncio.sleep(delay)
    store.apply_verification_reply(run_id, vid, answer, source="simulated-rep")


def _mock_answer(zone_id: str, neighbor_id: str, first: bool) -> str:
    if first:
        return "yes"
    h = int(hashlib.md5(f"{zone_id}:{neighbor_id}".encode()).hexdigest(), 16) % 10
    return "yes" if h < 6 else "unsure" if h < 9 else "no"


async def neighbor_verification_node(state: dict) -> dict:
    rid = state["run_id"]
    zones = state["silent_zones"]
    villages = data_loader.load_villages()
    shapes = geo.build_flood_shapes(data_loader.load_flood())
    outside = [v for v in villages if not geo.point_flood_info(v["lat"], v["lon"], shapes)]

    verifs: list[dict] = []
    store.set_section(rid, "verifications", verifs)
    tasks = []
    counter = 0

    async with httpx.AsyncClient() as client:
        for z in zones:
            geo_info = await geo.reverse_geocode(client, z["lat"], z["lon"], z.get("district") or "Rajanpur")
            z["district"] = geo_info["district"]
            store.log(rid, AGENT, f"{z['id']} {z['name']}: reverse geocode ({geo_info['source']}) -> {geo_info['district']}")

            cands = []
            for v in outside:
                d = geo.haversine_km(z["lat"], z["lon"], v["lat"], v["lon"])
                cands.append({**v, "distance_km": round(d, 1), "source": "hdx"})
            for p in await geo.search_villages(client, z["lat"], z["lon"], settings.max_radius_km):
                if geo.point_flood_info(p["lat"], p["lon"], shapes):
                    continue
                d = geo.haversine_km(z["lat"], z["lon"], p["lat"], p["lon"])
                cands.append({"id": f"OSM-{abs(hash(p['name'])) % 10000}", "name": p["name"], "lat": p["lat"],
                              "lon": p["lon"], "population": None, "rep": f"{p['name']} representative",
                              "distance_km": round(d, 1), "source": "osm"})
            in_range = _dedupe([c for c in cands if settings.min_radius_km <= c["distance_km"] <= settings.max_radius_km])
            if not in_range:
                in_range = _dedupe([c for c in cands if c["distance_km"] <= 15])[:settings.max_neighbors]
                store.log(rid, AGENT, f"{z['id']}: nobody in {settings.min_radius_km}-{settings.max_radius_km} km, widened to 15 km.", "warn")
            chosen = in_range[:settings.max_neighbors]
            z["neighbors"] = [{"id": c["id"], "name": c["name"], "lat": c["lat"], "lon": c["lon"],
                               "distance_km": c["distance_km"], "source": c["source"]} for c in chosen]
            if not chosen:
                store.log(rid, AGENT, f"{z['id']}: no neighboring settlement found - zone stays UNVERIFIED.", "warn")

            for idx, c in enumerate(chosen):
                counter += 1
                vid = f"V{counter}"
                question = (f"Salaam {c['rep']}. Is {z['name']} cut off? Do you observe flood water around it? "
                            f"(کیا {z['name']} پانی میں گھرا ہوا اور رابطے سے کٹا ہوا ہے؟)")
                rec = {"id": vid, "zone_id": z["id"], "zone_name": z["name"], "neighbor_id": c["id"],
                       "neighbor_name": c["name"], "rep": c["rep"], "lat": c["lat"], "lon": c["lon"],
                       "distance_km": c["distance_km"], "question": question, "status": "pending",
                       "sent_at": store.now()}
                verifs.append(rec)
                buttons = [("Yes - cut off", f"vf|{rid}|{vid}|yes"), ("No flooding", f"vf|{rid}|{vid}|no"),
                           ("Not sure", f"vf|{rid}|{vid}|unsure")]
                await telegram.send_message(client, chat_id=settings.telegram_village_chat,
                                            text=f"[{c['name']} - {c['distance_km']} km away]\n{question}",
                                            to_label=f"{c['name']} rep ({c['rep']})", channel="village-verification",
                                            buttons=buttons, run_id=rid)
                store.log(rid, AGENT, f"Asked {c['name']} rep ({c['distance_km']} km away) about {z['name']}.")
                if not settings.telegram_enabled and settings.mock_auto_reply:
                    ans = _mock_answer(z["id"], c["id"], idx == 0)
                    tasks.append(asyncio.create_task(_auto_reply(rid, vid, ans, random.uniform(0.6, 2.0))))

        deadline = time.time() + settings.verify_timeout
        while time.time() < deadline and any(v["status"] == "pending" for v in verifs):
            await asyncio.sleep(0.5)
    for v in verifs:
        if v["status"] == "pending":
            v["status"] = "timeout"
            store.log(rid, AGENT, f"No reply from {v['neighbor_name']} in time (timeout).", "warn")

    for z in zones:
        answers = [v["status"] for v in verifs if v["zone_id"] == z["id"]]
        if "yes" in answers:
            status = "CONFIRMED_CUT_OFF"
        elif answers and all(a == "no" for a in answers):
            status = "NOT_CONFIRMED"
        else:
            status = "UNVERIFIED"
        z["verification"] = {"status": status, **{k: answers.count(k) for k in ("yes", "no", "unsure", "timeout")}}
        store.log(rid, AGENT, f"{z['id']} {z['name']}: {status} "
                              f"(yes={answers.count('yes')}, no={answers.count('no')}, unsure={answers.count('unsure')}, "
                              f"timeout={answers.count('timeout')}).",
                  "success" if status == "CONFIRMED_CUT_OFF" else "warn")
    store.set_section(rid, "silent_zones", zones)
    return {"silent_zones": zones, "verifications": verifs}
