from __future__ import annotations
from pathlib import Path
import json
import networkx as nx
from cqia.analysis.dependency_graph import write_dep_json
from cqia.reporting.schema import ReportJSON, FindingJSON, DepMetricsJSON, ScanSummaryJSON

def export_dependency_graph(G: nx.DiGraph, reports_dir: Path) -> Path:
    out = reports_dir / "dep-graph.json"
    return write_dep_json(G, out)

def export_json_report(
    reports_dir: Path,
    files_scanned: int,
    by_language: dict[str, int],
    findings: list[FindingJSON],
    dep_metrics: DepMetricsJSON,
) -> Path:
    out = reports_dir / "report.json"
    payload = ReportJSON(
        summary=ScanSummaryJSON(files_scanned=files_scanned, by_language=by_language),
        findings=findings,
        dependencies=dep_metrics,
    )
    out.write_text(json.dumps(payload.model_dump(), indent=2), encoding="utf-8")
    return out
