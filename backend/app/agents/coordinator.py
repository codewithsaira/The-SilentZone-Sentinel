"""Agent 4 - Coordinator: evaluates bids, picks the best rescue combination, explains it in English + Urdu,
and posts it for one-click human approval."""
import httpx

from .. import store
from ..config import settings
from ..services import llm, telegram
from .resource_agents import FLEET, FLEET_BY_ID, zone_needs

AGENT = "Coordinator"
VERIF_MULT = {"CONFIRMED_CUT_OFF": 1.5, "UNVERIFIED": 1.0, "NOT_CONFIRMED": 0.4}
VERIF_UR = {"CONFIRMED_CUT_OFF": "تصدیق شدہ طور پر محصور", "UNVERIFIED": "غیر تصدیق شدہ"}
SEPARATOR = "=====URDU====="


def _unit(b: dict) -> dict:
    return {k: b[k] for k in ("agent_id", "agent", "eta_min", "feasibility", "resource_match",
                              "distance_km", "route", "base", "assets_offered")}


def _top_caps(agent_id: str, needs: dict, n: int = 2) -> list[str]:
    caps = FLEET_BY_ID[agent_id]["capabilities"]
    return [k for k, _ in sorted(((k, needs[k] * caps[k]) for k in needs), key=lambda kv: -kv[1])[:n]]


def _template(assignments: list, held: list, sev: dict) -> tuple[str, str]:
    pop = sum(a["population"] for a in assignments)
    en = [f"EXECUTIVE SUMMARY - The SilentZone Sentinel found {len(assignments) + len(held)} Silent Zone(s) inside the flood "
          f"footprint (zero SOS received, flood severity {sev['level']}). Population in recommended dispatch: ~{pop}."]
    ur = [f"خلاصہ: دی سائلنٹ زون سینٹینیل کے مطابق سیلابی علاقے میں {len(assignments) + len(held)} 'خاموش زون' کی نشاندہی ہوئی ہے جہاں سے کوئی SOS موصول نہیں ہوا۔ "
          f"سیلاب کی شدت: {sev['level']}۔ سفارش کردہ امداد میں تقریباً {pop} افراد شامل ہیں۔"]
    for a in assignments:
        p, s = a["primary"], a.get("secondary")
        line = (f"- {a['zone_name']} ({a['population']} people, neighbour check: {a['verification']['status']}): send "
                f"{p['agent']} first (ETA ~{p['eta_min']} min, feasibility {p['feasibility']})")
        urd = (f"- {a['zone_name']}: آبادی تقریباً {a['population']}، پڑوسی دیہات کی تصدیق: "
               f"{VERIF_UR.get(a['verification']['status'], 'غیر تصدیق شدہ')}۔ سب سے پہلے {p['agent']} روانہ کریں "
               f"(پہنچنے کا اندازہ تقریباً {p['eta_min']} منٹ)")
        if s:
            line += f", with {s['agent']} in support (ETA ~{s['eta_min']} min) covering: {', '.join(a['support_covers']) or 'extra capacity'}"
            urd += f"، اور معاونت کے لیے {s['agent']} (تقریباً {s['eta_min']} منٹ)"
        en.append(line + f". Why: {a['reason']}")
        ur.append(urd + "۔")
    for h in held:
        en.append(f"- HOLD {h['zone_name']}: {h['reason']}")
        ur.append(f"- {h['zone_name']}: فی الحال روکا گیا ہے۔")
    en.append("Final decision requires human coordinator approval before any unit moves.")
    ur.append("حتمی فیصلہ انسانی کوآرڈینیٹر کی منظوری سے مشروط ہے۔")
    return "\n".join(en), "\n".join(ur)


def _prompt(assignments: list, held: list, sev: dict) -> str:
    import json
    slim = [{k: v for k, v in a.items() if k not in ("primary", "secondary")} |
            {"primary": {k: v for k, v in a["primary"].items() if k not in ("route", "base", "assets_offered")},
             "secondary": ({k: v for k, v in a["secondary"].items() if k not in ("route", "base", "assets_offered")}
                           if a.get("secondary") else None)} for a in assignments]
    return (
        "You are the Coordinator of a flood-response system. Using ONLY the JSON facts below, write (1) a plain-English "
        "executive explanation (max 170 words) of the dispatch recommendation and why each unit was chosen, then a line "
        f"containing exactly {SEPARATOR}, then (2) the same explanation in clear Urdu (Urdu script). "
        "Do not invent numbers. End by stating that a human must approve.\n\n"
        f"Flood severity: {sev}\nAssignments: {json.dumps(slim, ensure_ascii=False)}\nHeld zones: {json.dumps(held, ensure_ascii=False)}"
    )


async def coordinator_node(state: dict) -> dict:
    rid = state["run_id"]
    zones, bids, sev = state["silent_zones"], state["bids"], state["severity"]
    for z in zones:
        z["priority"] = round(z["population"] * (1 + sev["index"]) * VERIF_MULT[z["verification"]["status"]])
    teams_left = {a["id"]: a["teams"] for a in FLEET}
    assignments, held = [], []

    store.log(rid, AGENT, "Evaluating bids: pass 1 gives every verified zone a primary unit, pass 2 adds support units from leftover teams.")
    ranked = sorted(zones, key=lambda z: -z["priority"])
    # ---- pass 1: primary unit per zone, highest priority first
    for z in ranked:
        if z["verification"]["status"] == "NOT_CONFIRMED":
            held.append({"zone_id": z["id"], "zone_name": z["name"],
                         "reason": "Neighbors observe no flooding - hold and re-check (drone / second source) before committing units."})
            continue
        viable = [b for b in bids if b["zone_id"] == z["id"] and not b["declined"] and teams_left[b["agent_id"]] > 0]
        if not viable:
            held.append({"zone_id": z["id"], "zone_name": z["name"],
                         "reason": "All teams are already committed to higher-priority zones - queue for the next free unit."})
            store.log(rid, AGENT, f"{z['id']} {z['name']}: no free team left, queued.", "warn")
            continue
        needs = zone_needs(z)
        primary = max(viable, key=lambda b: b["feasibility"])
        teams_left[primary["agent_id"]] -= 1
        strengths = " and ".join(_top_caps(primary["agent_id"], needs))
        fastest = primary["eta_min"] == min(b["eta_min"] for b in viable)
        reason = (f"best overall feasibility ({primary['feasibility']}), strongest on {strengths}"
                  + (", and the fastest available arrival" if fastest else ""))
        assignments.append({
            "zone_id": z["id"], "zone_name": z["name"], "population": z["population"], "priority": z["priority"],
            "verification": z["verification"], "lat": z["lat"], "lon": z["lon"], "needs": needs,
            "primary": _unit(primary), "secondary": None, "support_covers": [], "reason": reason})
        store.log(rid, AGENT, f"{z['id']} {z['name']}: PRIMARY {primary['agent']} "
                              f"(feasibility {primary['feasibility']}, ETA {primary['eta_min']} min).", "success")
    # ---- pass 2: complementary support unit where it adds real capability
    for a in assignments:
        pcaps = FLEET_BY_ID[a["primary"]["agent_id"]]["capabilities"]
        cands = [b for b in bids if b["zone_id"] == a["zone_id"] and not b["declined"]
                 and b["agent_id"] != a["primary"]["agent_id"] and teams_left[b["agent_id"]] > 0
                 and b["feasibility"] >= 0.45]
        best, best_gain = None, 0.0
        for b in cands:
            caps = FLEET_BY_ID[b["agent_id"]]["capabilities"]
            gain = sum(a["needs"][k] * max(0.0, caps[k] - pcaps[k]) for k in a["needs"])
            if gain > best_gain:
                best, best_gain = b, gain
        if best and best_gain >= 0.12:
            teams_left[best["agent_id"]] -= 1
            scaps = FLEET_BY_ID[best["agent_id"]]["capabilities"]
            a["secondary"] = _unit(best)
            a["support_covers"] = [k for k in scaps if scaps[k] >= 0.6 > pcaps[k]]
            store.log(rid, AGENT, f"{a['zone_id']} {a['zone_name']}: SUPPORT {best['agent']} "
                                  f"(adds {', '.join(a['support_covers']) or 'capacity'}).", "success")
    assignments.sort(key=lambda a: -a["priority"])

    async with httpx.AsyncClient() as client:
        text, provider = None, "template"
        if assignments:
            store.log(rid, AGENT, f"Writing English + Urdu explanation (provider: {llm.describe()}).")
            text, provider = await llm.generate(client, _prompt(assignments, held, sev))
        english, urdu = _template(assignments, held, sev)
        if text and SEPARATOR in text:
            en_llm, ur_llm = text.split(SEPARATOR, 1)
            if en_llm.strip() and ur_llm.strip():
                english, urdu = en_llm.strip(), ur_llm.strip()
            else:
                provider = "template"
        else:
            provider = "template"

        dispatch = {"id": f"D-{rid}", "status": "pending" if assignments else "no_action", "assignments": assignments,
                    "held": held, "english": english, "urdu": urdu, "explanation_source": provider,
                    "created": store.now()}
        store.RUNS[rid]["dispatch"] = dispatch
        store.set_section(rid, "silent_zones", zones)

        if assignments:
            store.set_status(rid, "awaiting_approval")
            buttons = [("Approve Dispatch", f"dp|{rid}|approve"), ("Reject", f"dp|{rid}|reject")]
            await telegram.send_message(client, chat_id=settings.telegram_coordinator_chat,
                                        text=f"THE SILENTZONE SENTINEL - DISPATCH RECOMMENDATION\n\n{english}\n\n{urdu}",
                                        to_label="Human coordinator channel", channel="coordinator-approval",
                                        buttons=buttons, run_id=rid)
            store.log(rid, AGENT, "Dispatch recommendation posted for human approval (Approve / Reject).", "success")
        else:
            store.set_status(rid, "completed")
            store.log(rid, AGENT, "No units dispatched - all zones held or unserviceable.", "warn")
    return {"dispatch": dispatch}
