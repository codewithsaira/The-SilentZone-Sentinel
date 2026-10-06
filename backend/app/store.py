"""In-memory state: runs, the simulated Telegram outbox, and demo SOS injections."""
import time
import uuid
from typing import Any, Optional

RUNS: dict[str, dict] = {}
OUTBOX: list[dict] = []
EXTRA_SOS: list[dict] = []


def now() -> str:
    return time.strftime("%H:%M:%S")


def new_run() -> dict:
    rid = uuid.uuid4().hex[:8]
    RUNS[rid] = {
        "id": rid,
        "status": "running",
        "created": time.time(),
        "logs": [],
        "sections": {},
        "dispatch": None,
    }
    return RUNS[rid]


def log(run_id: str, agent: str, message: str, level: str = "info") -> None:
    run = RUNS.get(run_id)
    if run is not None:
        run["logs"].append({"t": now(), "agent": agent, "level": level, "message": message})


def set_section(run_id: str, key: str, value: Any) -> None:
    RUNS[run_id]["sections"][key] = value


def set_status(run_id: str, status: str) -> None:
    RUNS[run_id]["status"] = status


def add_outbox(*, channel: str, to: str, text: str, buttons: Optional[list] = None,
               run_id: Optional[str] = None, delivered: str = "simulated") -> None:
    OUTBOX.append({
        "t": now(), "channel": channel, "to": to, "text": text,
        "buttons": [b[0] for b in (buttons or [])], "run_id": run_id, "delivered": delivered,
    })


def apply_verification_reply(run_id: str, vid: str, answer: str, source: str = "telegram") -> str:
    run = RUNS.get(run_id)
    if not run:
        return "Run not found"
    for v in run["sections"].get("verifications", []):
        if v["id"] == vid:
            if v["status"] != "pending":
                return "Already answered"
            v["status"] = answer
            v["answered_at"] = now()
            v["answer_source"] = source
            log(run_id, "Neighbor Verification",
                f"Reply from {v['neighbor_name']} rep ({source}): '{answer}' about {v['zone_name']}")
            return "Thanks - recorded."
    return "Unknown verification"


def decide(run_id: str, decision: str) -> str:
    run = RUNS.get(run_id)
    if not run or not run.get("dispatch"):
        return "No dispatch to decide on"
    d = run["dispatch"]
    if d["status"] != "pending":
        return f"Already {d['status']}"
    approved = decision == "approve"
    d["status"] = "approved" if approved else "rejected"
    run["status"] = d["status"]
    log(run_id, "Coordinator",
        "Human coordinator APPROVED the dispatch - orders released (simulated)." if approved
        else "Human coordinator REJECTED the dispatch - no units released.",
        "success" if approved else "warn")
    if approved:
        seen = set()
        for a in d["assignments"]:
            for role in ("primary", "secondary"):
                unit = a.get(role)
                if unit and (unit["agent"], a["zone_id"]) not in seen:
                    seen.add((unit["agent"], a["zone_id"]))
                    add_outbox(channel="agency-dispatch", to=unit["agent"], run_id=run_id,
                               text=f"DISPATCH ORDER: proceed to {a['zone_name']} "
                                    f"(~{a['population']} people). Role: {role}. ETA ~{unit['eta_min']} min.")
    return "Approved" if approved else "Rejected"
