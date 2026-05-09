
from __future__ import annotations
from langgraph.graph import StateGraph, END
from agents.nodes import ingest, classify, extract, critique, revise, State
from agents.hash_subjects import spec_hash_subject
from agents.instrumentation import traced_node
from utils.render import render_markdown

@traced_node("render", hash_subject=lambda state: spec_hash_subject(state.get("spec", {})))
async def render(state: State) -> State:
    target = state.get("target","PRD")
    tmpl = "prd.md.j2" if target == "PRD" else ("githubspec.md.j2" if target == "GitHubSpec" else "techspec.md.j2")
    if "spec" not in state:
        return {}
    spec = {
        **state["spec"],
        "rendered_markdown": render_markdown(state["spec"], tmpl),
    }
    return {"spec": spec}

def build_graph():
    g = StateGraph(State)
    g.add_node("ingest", ingest)
    g.add_node("classify", classify)
    g.add_node("extract", extract)
    g.add_node("critique", critique)
    g.add_node("revise", revise)
    g.add_node("render", render)
    g.set_entry_point("ingest")
    g.add_edge("ingest","classify")
    g.add_edge("classify","extract")
    g.add_edge("extract","critique")
    g.add_edge("critique","revise")
    g.add_edge("revise","render")
    g.add_edge("render", END)
    return g.compile()
