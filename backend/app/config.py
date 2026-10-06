"""Central configuration. Everything comes from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.offline_mode = _bool("OFFLINE_MODE", False)
        self.http_timeout = float(os.getenv("HTTP_TIMEOUT_SEC", "8"))

        self.open_meteo_url = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
        self.osrm_url = os.getenv("OSRM_URL", "https://router.project-osrm.org").rstrip("/")
        self.nominatim_url = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org").rstrip("/")
        self.nominatim_user_agent = os.getenv(
            "NOMINATIM_USER_AGENT", "khamoshi-radar-prototype/0.1 (contact: you@example.com)"
        )
        self.weather_demo_boost_mm = float(os.getenv("WEATHER_DEMO_BOOST_MM", "0") or 0)

        self.llm_provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")

        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_coordinator_chat = os.getenv("TELEGRAM_COORDINATOR_CHAT_ID", "").strip()
        self.telegram_village_chat = (
            os.getenv("TELEGRAM_VILLAGE_CHAT_ID", "").strip() or self.telegram_coordinator_chat
        )

        self.min_radius_km = float(os.getenv("MIN_RADIUS_KM", "3"))
        self.max_radius_km = float(os.getenv("MAX_RADIUS_KM", "10"))
        self.max_neighbors = int(os.getenv("MAX_NEIGHBORS_PER_ZONE", "2"))
        self.verify_timeout = float(os.getenv("VERIFY_TIMEOUT_SEC", "25"))
        self.mock_auto_reply = _bool("MOCK_AUTO_REPLY", True)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.telegram_coordinator_chat) and not self.offline_mode


settings = Settings()
