"""LangGraph pipeline: silence_radar -> neighbor_verification -> negotiation -> coordinator."""
import traceback
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import store
from .agents.coordinator import coordinator_node
from .agents.neighbor_verification import neighbor_verification_node
from .agents.resource_agents import negotiation_node
from .agents.silence_radar import silence_radar_node


class PipelineState(TypedDict, total=False):
    run_id: str
    weather: dict
    severity: dict
    silent_zones: list
    verifications: list
    bids: list
    dispatch: dict


def _after_radar(state: PipelineState) -> str:
    return "neighbor_verification" if state.get("silent_zones") else "done"


def _after_verification(state: PipelineState) -> str:
    live = [z for z in state["silent_zones"] if z["verification"]["status"] != "NOT_CONFIRMED"]
    return "negotiation" if live else "coordinator"


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("silence_radar", silence_radar_node)
    g.add_node("neighbor_verification", neighbor_verification_node)
    g.add_node("negotiation", negotiation_node)
    g.add_node("coordinator", coordinator_node)
    g.add_edge(START, "silence_radar")
    g.add_conditional_edges("silence_radar", _after_radar,
                            {"neighbor_verification": "neighbor_verification", "done": END})
    g.add_conditional_edges("neighbor_verification", _after_verification,
                            {"negotiation": "negotiation", "coordinator": "coordinator"})
    g.add_edge("negotiation", "coordinator")
    g.add_edge("coordinator", END)
    return g.compile()


GRAPH = build_graph()


async def run_pipeline(run_id: str) -> None:
    try:
        store.log(run_id, "System", "Pipeline started: Silence Radar -> Neighbor Verification -> Negotiation -> Coordinator.")
        state = await GRAPH.ainvoke({"run_id": run_id, "bids": []})
        if not state.get("silent_zones"):
            store.set_status(run_id, "no_silent_zones")
            store.log(run_id, "System", "No Silent Zones: every flooded settlement has reported an SOS.", "success")
    except Exception as e:  # surface the failure to the UI instead of dying silently
        store.set_status(run_id, "error")
        store.log(run_id, "System", f"Pipeline error: {type(e).__name__}: {e}", "error")
        traceback.print_exc()
