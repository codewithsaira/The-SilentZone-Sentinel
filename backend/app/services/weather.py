"""Open-Meteo precipitation + soil moisture (free, no API key)."""
import httpx

from ..config import settings


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


async def fetch_weather(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    result = None
    if not settings.offline_mode:
        try:
            r = await client.get(settings.open_meteo_url, params={
                "latitude": round(lat, 4), "longitude": round(lon, 4),
                "hourly": "precipitation,soil_moisture_0_to_1cm",
                "past_days": 3, "forecast_days": 2, "timezone": "auto",
            }, timeout=settings.http_timeout)
            r.raise_for_status()
            hourly = r.json()["hourly"]
            precip = [x or 0.0 for x in hourly["precipitation"]]
            soil = [x for x in hourly.get("soil_moisture_0_to_1cm", []) if x is not None]
            past = sum(precip[:72])
            future = sum(precip[72:])
            recent_soil = soil[48:72] or soil[-24:] or [0.3]
            soil_mean = sum(recent_soil) / len(recent_soil)
            result = {
                "source": "open-meteo",
                "rain_past_3d_mm": round(past, 1),
                "rain_forecast_mm": round(future, 1),
                "soil_moisture": round(soil_mean, 3),
                "soil_saturation": round(_clamp(soil_mean / 0.45), 2),
            }
        except Exception:
            result = None
    if result is None:
        result = {"source": "mock", "rain_past_3d_mm": 186.0, "rain_forecast_mm": 42.0,
                  "soil_moisture": 0.41, "soil_saturation": 0.91}
    if settings.weather_demo_boost_mm:
        result["rain_past_3d_mm"] = round(result["rain_past_3d_mm"] + settings.weather_demo_boost_mm, 1)
        result["demo_boost_mm"] = settings.weather_demo_boost_mm
    return result


def severity_from_weather(w: dict) -> dict:
    index = 0.6 * _clamp(w["rain_past_3d_mm"] / 150.0) + 0.4 * w["soil_saturation"]
    level = "EXTREME" if index >= 0.7 else "HIGH" if index >= 0.4 else "MODERATE"
    return {"index": round(index, 2), "level": level}
