from __future__ import annotations
from typing import Literal, Dict, Any

from langgraph.graph import StateGraph, START, END
from cqia.agent.graph.state import CQIAState
from cqia.agent.graph.nodes import guardrails, analyze_node, chat_node

def _route_after_guardrails(state: CQIAState) -> Literal["analyze_node", "chat_node", "end"]:
    nxt = state.get("next_action") or "end"
    if nxt == "run_analyze":
        return "analyze_node"
    if nxt == "run_chat":
        return "chat_node"
    return "end"

def build_cqia_graph() -> Any:
    builder = StateGraph(CQIAState)
    builder.add_node("guardrails", guardrails)
    builder.add_node("analyze_node", analyze_node)
    builder.add_node("chat_node", chat_node)

    builder.add_edge(START, "guardrails")
    builder.add_conditional_edges("guardrails", _route_after_guardrails, {
        "analyze_node": "analyze_node",
        "chat_node": "chat_node",
        "end": END,
    })
    builder.add_edge("analyze_node", END)
    builder.add_edge("chat_node", END)
    return builder.compile()
