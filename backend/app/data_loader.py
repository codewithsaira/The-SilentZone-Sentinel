"""Loads the scenario: simulated flood polygons, HDX-style settlements and the SOS inbox."""
import csv
import json
from collections import Counter
from pathlib import Path

from . import store
from .services import geo

DATA = Path(__file__).resolve().parents[1] / "data"


def load_flood() -> dict:
    return json.loads((DATA / "flood.geojson").read_text(encoding="utf-8"))


def load_villages() -> list[dict]:
    """Uses backend/data/hdx_settlements.csv if present (columns: name,lat,lon,population),
    otherwise the bundled mock settlements."""
    csv_path = DATA / "hdx_settlements.csv"
    if csv_path.exists():
        out = []
        with csv_path.open(encoding="utf-8-sig") as f:
            for i, row in enumerate(csv.DictReader(f), start=1):
                lat = row.get("lat") or row.get("latitude")
                lon = row.get("lon") or row.get("longitude")
                if not lat or not lon:
                    continue
                out.append({
                    "id": row.get("id") or f"H{i:04d}",
                    "name": row.get("name") or f"Settlement {i}",
                    "lat": float(lat), "lon": float(lon),
                    "population": int(float(row.get("population") or row.get("pop") or 500)),
                    "district": row.get("district") or "Unknown",
                    "rep": row.get("rep") or "Village representative",
                })
        if out:
            return out
    return json.loads((DATA / "villages.json").read_text(encoding="utf-8"))


def load_sos() -> list[dict]:
    base = json.loads((DATA / "sos_feed.json").read_text(encoding="utf-8"))
    return base + list(store.EXTRA_SOS)


def sos_counts(villages: list[dict], sos: list[dict]) -> Counter:
    """SOS entries carry a village_id, or lat/lon that is matched to the nearest settlement (<3 km)."""
    counts: Counter = Counter()
    for s in sos:
        if s.get("village_id"):
            counts[s["village_id"]] += 1
        elif "lat" in s and "lon" in s:
            best = min(villages, key=lambda v: geo.haversine_km(s["lat"], s["lon"], v["lat"], v["lon"]))
            if geo.haversine_km(s["lat"], s["lon"], best["lat"], best["lon"]) <= 3.0:
                counts[best["id"]] += 1
    return counts
