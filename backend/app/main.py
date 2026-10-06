"""FastAPI service exposing the Khamoshi Radar pipeline to the Streamlit UI (and Telegram callbacks)."""
import asyncio
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import data_loader, store
from .agents.resource_agents import FLEET
from .config import settings
from .graph import run_pipeline
from .services import geo, llm, telegram

_tasks: set = set()


def handle_callback(data: str) -> str:
    """Telegram inline-button callbacks: 'vf|run|vid|answer' and 'dp|run|approve|reject'."""
    parts = data.split("|")
    if parts[0] == "vf" and len(parts) == 4:
        return store.apply_verification_reply(parts[1], parts[2], parts[3], source="telegram")
    if parts[0] == "dp" and len(parts) == 3:
        return store.decide(parts[1], parts[2])
    return "Unknown action"


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(telegram.poll_updates(handle_callback)) if settings.telegram_enabled else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="The SilentZone Sentinel API", version="0.1", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SosIn(BaseModel):
    village_id: str
    text: str = "Simulated SOS"


class ReplyIn(BaseModel):
    vid: str
    answer: Literal["yes", "no", "unsure"]


@app.get("/api/health")
def health():
    return {"ok": True, "offline_mode": settings.offline_mode, "telegram": settings.telegram_enabled,
            "llm": llm.describe()}


@app.get("/api/scenario")
def scenario():
    flood = data_loader.load_flood()
    villages = data_loader.load_villages()
    counts = data_loader.sos_counts(villages, data_loader.load_sos())
    shapes = geo.build_flood_shapes(flood)
    out = []
    for v in villages:
        info = geo.point_flood_info(v["lat"], v["lon"], shapes)
        out.append({**v, "sos_count": counts.get(v["id"], 0), "in_flood": bool(info),
                    "flood_depth_m": info["depth_m"] if info else 0})
    return {"flood": flood, "villages": out,
            "bases": [{"id": a["id"], "name": a["name"], **a["base"], "tagline": a["tagline"]} for a in FLEET]}


@app.post("/api/sos")
def add_sos(body: SosIn):
    if body.village_id not in {v["id"] for v in data_loader.load_villages()}:
        raise HTTPException(404, "Unknown village_id")
    store.EXTRA_SOS.append({"id": f"X{len(store.EXTRA_SOS) + 1}", "village_id": body.village_id,
                            "ts": store.now(), "text": body.text})
    return {"ok": True, "extra_sos": len(store.EXTRA_SOS)}


@app.post("/api/sos/reset")
def reset_sos():
    store.EXTRA_SOS.clear()
    return {"ok": True}


@app.post("/api/runs")
async def start_run():
    run = store.new_run()
    t = asyncio.create_task(run_pipeline(run["id"]))
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)
    return {"run_id": run["id"]}


def _get(run_id: str) -> dict:
    run = store.RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    return _get(run_id)


@app.post("/api/runs/{run_id}/verification")
def manual_reply(run_id: str, body: ReplyIn):
    _get(run_id)
    return {"message": store.apply_verification_reply(run_id, body.vid, body.answer, source="ui")}


@app.post("/api/runs/{run_id}/approve")
def approve(run_id: str):
    _get(run_id)
    return {"message": store.decide(run_id, "approve")}


@app.post("/api/runs/{run_id}/reject")
def reject(run_id: str):
    _get(run_id)
    return {"message": store.decide(run_id, "reject")}


@app.get("/api/outbox")
def outbox():
    return store.OUTBOX[-100:]
