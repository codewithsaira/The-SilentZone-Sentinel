"""Geometry helpers plus the free OSRM (routing) and Nominatim (OpenStreetMap geocoding) clients."""
import asyncio
import math
import time
from typing import Optional

import httpx
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from ..config import settings


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def build_flood_shapes(geojson: dict) -> list:
    return [(shape(f["geometry"]), f.get("properties", {})) for f in geojson["features"]]


def point_flood_info(lat: float, lon: float, shapes: list) -> Optional[dict]:
    pt = Point(lon, lat)
    depth, name = None, None
    for geom, props in shapes:
        if geom.covers(pt):
            d = float(props.get("depth_m", 1.0))
            if depth is None or d > depth:
                depth, name = d, props.get("name")
    return None if depth is None else {"depth_m": depth, "polygon": name}


def flood_centroid(shapes: list) -> tuple[float, float]:
    c = unary_union([g for g, _ in shapes]).centroid
    return c.y, c.x


# ---------------------------------------------------------------- OSRM
_route_cache: dict = {}


async def osrm_route(client: httpx.AsyncClient, a: tuple, b: tuple) -> dict:
    """Driving route a->b ((lat, lon) tuples). Falls back to a haversine estimate."""
    key = (round(a[0], 4), round(a[1], 4), round(b[0], 4), round(b[1], 4))
    if key in _route_cache:
        return _route_cache[key]
    result = None
    if not settings.offline_mode:
        try:
            url = f"{settings.osrm_url}/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}"
            r = await client.get(url, params={"overview": "simplified", "geometries": "geojson"},
                                 timeout=settings.http_timeout)
            r.raise_for_status()
            rt = r.json()["routes"][0]
            result = {
                "distance_km": rt["distance"] / 1000.0,
                "duration_min": rt["duration"] / 60.0,
                "geometry": [[y, x] for x, y in rt["geometry"]["coordinates"]],
                "source": "osrm",
            }
        except Exception:
            result = None
    if result is None:
        d = haversine_km(a[0], a[1], b[0], b[1]) * 1.35  # crude road-winding factor
        result = {
            "distance_km": d,
            "duration_min": d / 40.0 * 60.0,
            "geometry": [[a[0], a[1]], [b[0], b[1]]],
            "source": "haversine-fallback",
        }
    _route_cache[key] = result
    return result


# ---------------------------------------------------------------- Nominatim
_nom_lock = asyncio.Lock()
_nom_last = 0.0


async def _nom_get(client: httpx.AsyncClient, path: str, params: dict):
    """Nominatim usage policy: max 1 request/second and an identifying User-Agent."""
    global _nom_last
    async with _nom_lock:
        wait = 1.1 - (time.monotonic() - _nom_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            r = await client.get(f"{settings.nominatim_url}{path}", params=params,
                                 headers={"User-Agent": settings.nominatim_user_agent},
                                 timeout=settings.http_timeout)
        finally:
            _nom_last = time.monotonic()
    r.raise_for_status()
    return r.json()


async def reverse_geocode(client: httpx.AsyncClient, lat: float, lon: float, fallback: str) -> dict:
    if not settings.offline_mode:
        try:
            j = await _nom_get(client, "/reverse", {"format": "jsonv2", "lat": lat, "lon": lon,
                                                    "zoom": 10, "accept-language": "en"})
            addr = j.get("address", {})
            district = addr.get("county") or addr.get("state_district") or addr.get("city") or fallback
            return {"display": j.get("display_name", fallback), "district": district, "source": "nominatim"}
        except Exception:
            pass
    return {"display": fallback, "district": fallback, "source": "dataset"}


async def search_villages(client: httpx.AsyncClient, lat: float, lon: float, radius_km: float) -> list:
    """Best-effort OSM lookup of villages in a bounding box around (lat, lon)."""
    if settings.offline_mode:
        return []
    try:
        dlat = radius_km / 111.0
        dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
        j = await _nom_get(client, "/search", {
            "q": "village", "format": "jsonv2", "bounded": 1, "limit": 15,
            "viewbox": f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}",
        })
        out = []
        for it in j:
            name = it.get("name") or (it.get("display_name", "").split(",")[0])
            if name:
                out.append({"name": name, "lat": float(it["lat"]), "lon": float(it["lon"])})
        return out
    except Exception:
        return []
