from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple, List
import json
import networkx as nx

def _id(x) -> str:
    return str(x)

@dataclass(frozen=True)
class DepEdge:
    src: str
    dst: str

@dataclass
class DepMetrics:
    fan_in: Dict[str, int]
    fan_out: Dict[str, int]
    cycles: List[List[str]]
    top_fan_in: List[Tuple[str, int]]
    top_fan_out: List[Tuple[str, int]]

def build_dep_graph(edges: Iterable[DepEdge]) -> tuple[nx.DiGraph, DepMetrics]:
    G = nx.DiGraph()
    for e in edges:
        src = _id(e.src).strip()
        dst = _id(e.dst).strip()
        if not src or not dst or src == dst:
            continue
        G.add_edge(src, dst)
    fan_in = { _id(n): int(G.in_degree(n)) for n in G.nodes }
    fan_out = { _id(n): int(G.out_degree(n)) for n in G.nodes }
    try:
        raw_cycles = list(nx.simple_cycles(G))
    except Exception:
        raw_cycles = []
    top_fi = sorted(fan_in.items(), key=lambda x: x[1], reverse=True)[:10]
    top_fo = sorted(fan_out.items(), key=lambda x: x[1], reverse=True)[:10]
    metrics = DepMetrics(
        fan_in=fan_in,
        fan_out=fan_out,
        cycles=[[ _id(x) for x in c[:8] ] for c in raw_cycles[:10]],
        top_fan_in=top_fi,
        top_fan_out=top_fo
    )
    return G, metrics

def write_dep_json(G: nx.DiGraph, path):
    data = {
        "nodes": [{"id": _id(n)} for n in G.nodes],
        "edges": [{"source": _id(u), "target": _id(v)} for u, v in G.edges],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path
