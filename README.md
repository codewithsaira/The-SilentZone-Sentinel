# Khamoshi Radar (خاموشی ریڈار)

Multi-agent flood-response prototype that finds **Silent Zones**: villages that are under flood water but have
sent **zero SOS requests**. Silence during a flood can mean "no phone signal / no power / no one left to call",
so the system treats it as a signal, verifies it through neighbours, and prepares a human-approved dispatch.

**Everything is free.** No paid API, no credit card. With no keys at all it runs on built-in mocks; with
internet it uses Open-Meteo, OSRM and Nominatim (all keyless) and falls back to mocks if a call fails.

```
Silence Radar ──► Neighbor Verification ──► Negotiating Resource Agents ──► Coordinator ──► Human (Approve / Reject)
 flood polygon     Nominatim + OSM search     Rescue 1122 · Edhi · Al-Khidmat   bid evaluation     Streamlit card
 + villages        3-10 km, Telegram asks     OSRM routes → JSON bids           EN + Urdu text     or Telegram buttons
 + SOS + rain      village representatives                                      (Gemini/Ollama)
```

Built with FastAPI + LangGraph (backend) and Streamlit + Leaflet via folium (frontend).

## Run locally

Requires Python 3.10+.

```bash
cd khamoshi-radar
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                      # optional - works with zero keys

# terminal 1 - backend (from the khamoshi-radar folder)
uvicorn backend.app.main:app --reload --port 8000

# terminal 2 - frontend
streamlit run frontend/app.py
```

Open http://localhost:8501 and press **Launch multi-agent pipeline** in the sidebar. API docs: http://localhost:8000/docs

Force fully offline (no internet at all): set `OFFLINE_MODE=true` in `.env`.

## Demo script

1. Launch the pipeline. The radar finds 4 Silent Zones (flooded, 0 SOS) and marks them red on the map.
2. Neighbor Verification contacts representatives of dry villages 3-10 km away. In mock mode they reply automatically;
   set `MOCK_AUTO_REPLY=false` to answer by hand in the **Neighbor checks** tab.
3. Three resource agents bid per zone (OSRM routing, fuel, capability match). Watch the **Live agent log**.
4. The Coordinator allocates units and writes the English + Urdu explanation. Click **Approve Dispatch** or **Reject**.
5. Sidebar → *Send SOS* for a silent village → re-run: that village is no longer silent.

## What is real and what is mocked

| Piece | Live source | Offline / fallback |
|---|---|---|
| Rain + soil saturation | Open-Meteo forecast API (past 3 days + forecast) | fixed heavy-rain values |
| Routing / ETA | public OSRM demo server | haversine × 1.35 at 40 km/h |
| Geocoding, nearby villages | Nominatim (1 req/s, needs your contact in `NOMINATIM_USER_AGENT`) | bundled settlement list |
| Settlements + population | your HDX CSV (see below) | `backend/data/villages.json` (illustrative names) |
| Flood polygons | **simulated** `backend/data/flood.geojson` | same |
| SOS inbox | **simulated** `backend/data/sos_feed.json` | same |
| LLM explanation | Gemini free tier or local Ollama | deterministic English + Urdu template |
| Telegram | Bot API with inline buttons | in-app "Telegram sim" tab |

The flood extent, SOS feed, village names, and the three agencies' depot locations/fleet sizes are **illustrative
demo data**, not real incident or organisation data. Replace them before drawing any real-world conclusion.

### Using real HDX settlement data

Download a Pakistan settlements/populated-places dataset from https://data.humdata.org, export it to CSV with columns
`name,lat,lon,population` (optional: `id,district,rep`), and save it as `backend/data/hdx_settlements.csv`. It overrides
the mock list automatically. Replace `flood.geojson` with real inundation polygons (e.g. from satellite flood maps).

## Optional: free LLM

- **Gemini**: key from https://aistudio.google.com/app/apikey → `GEMINI_API_KEY=...`
- **Ollama (local)**: `ollama pull llama3 && ollama serve`, then `LLM_PROVIDER=ollama`
- Neither? The Coordinator uses its built-in template; the pipeline never depends on an LLM.

## Optional: real Telegram

1. Message **@BotFather** → `/newbot` → put the token in `TELEGRAM_BOT_TOKEN`.
2. Send any message to your bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` to read your `chat.id`.
3. Set `TELEGRAM_COORDINATOR_CHAT_ID` (and optionally `TELEGRAM_VILLAGE_CHAT_ID`; all "village rep" questions go to one
   chat in the demo). Restart the backend.

Inline buttons work through long-polling, so **no public URL or webhook is needed**. Approve/Reject in Telegram and in the
Streamlit card stay in sync.

## Project layout

```
backend/app/
  agents/        silence_radar.py · neighbor_verification.py · resource_agents.py · coordinator.py
  services/      geo.py (OSRM, Nominatim, shapely) · weather.py · telegram.py · llm.py
  graph.py       LangGraph pipeline          main.py   FastAPI endpoints
  store.py       in-memory runs, outbox      data_loader.py   scenario loading
backend/data/    flood.geojson · villages.json · sos_feed.json
frontend/app.py  Streamlit + folium command centre
```

## Notes and limits

- State is in memory: restarting the backend clears runs. Add a DB for anything beyond a prototype.
- A decision-support tool: the Coordinator only **recommends**; a human must approve before anything is dispatched.
- Public OSRM and Nominatim servers are for light/demo use; self-host them for heavier traffic.
- Bid scoring weights (match 0.4, ETA 0.3, fuel 0.2, capacity 0.1) are in `resource_agents.py` and easy to tune.
