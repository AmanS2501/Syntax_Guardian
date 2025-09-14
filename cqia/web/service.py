from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from cqia.web.clone import shallow_clone
from cqia.presets import load_rules
from cqia.analysis.severity import override_weights
from cqia.analysis.runner import run_analysis
from cqia.reporting.markdown import (
    write_basic_report,
    append_top_issues,
    append_per_category_summary,
    append_issue_details,
    append_findings,
    append_dependencies,
    append_dependency_outline,
)
from cqia.reporting.exporters import export_dependency_graph, export_json_report
from cqia.ingestion.walker import walk_repo

app = FastAPI(title="CQIA Web Service")

class AnalyzeRequest(BaseModel):
    github_url: str
    branch: Optional[str] = None
    include: Optional[List[str]] = ["**/*.py", "**/*.ts", "**/*.js"]
    exclude: Optional[List[str]] = [".git/**", "**/node_modules/**", "**/__pycache__/**", "**/.venv/**", "**/venv/**"]
    max_bytes: Optional[int] = 2_000_000
    clone_mode: Optional[str] = "clean"  # 'clean' or 'unique'

class AnalyzeResponse(BaseModel):
    repo_path: str
    report_md: Optional[str]
    report_json: Optional[str]
    files_scanned: int
    by_language: Dict[str, Any]
    top_issues: int

@app.post("/api/analyze", response_model=AnalyzeResponse)
def api_analyze(req: AnalyzeRequest):
    try:
        work = Path(".cqia-web-work")
        repo_root = shallow_clone(req.github_url, work, req.branch, req.clone_mode or "clean")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Clone failed: {e}")

    metas = walk_repo(repo_root, req.include or [], req.exclude or [], req.max_bytes or 2_000_000, follow_symlinks=False)
    if not metas:
        return AnalyzeResponse(
            repo_path=str(repo_root),
            report_md=None,
            report_json=None,
            files_scanned=0,
            by_language={},
            top_issues=0,
        )

    rules = load_rules(Path("presets/rules.yaml"))
    override_weights(rules.get("weights"))

    out_dir = repo_root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = write_basic_report(metas, out_dir)

    results = run_analysis(
        repo_root,
        req.include or [],
        req.exclude or [],
        rules=rules,
        max_bytes=req.max_bytes or 2_000_000,
        warn_at=rules.get("complexity", {}).get("warn_at", 10),
        dup_k=rules.get("duplication", {}).get("k_shingle", 7),
        dup_threshold=rules.get("duplication", {}).get("similarity_threshold", 0.90),
    )

    # Compose report
    append_top_issues(out_path, results.get("findings_scored", []))
    append_per_category_summary(out_path, results.get("findings_scored", []))
    append_issue_details(out_path, results.get("findings_scored", []))
    append_findings(out_path, results.get("findings_raw", {}))

    dep_graph = results.get("dep_graph") or results.get("dependencies", {}).get("graph")
    dep_metrics = results.get("dep_metrics") or results.get("dependencies", {}).get("metrics", {})
    if dep_graph is not None:
        export_dependency_graph(dep_graph, out_dir)
    append_dependencies(out_path, dep_metrics)
    append_dependency_outline(out_path, dep_metrics, results.get("hotspots", []))

    json_out = export_json_report(
        out_dir,
        files_scanned=len(metas),
        by_language=results.get("by_language", {}),
        findings=results.get("findings_json", []),
        dep_metrics=dep_metrics,
    )

    return AnalyzeResponse(
        repo_path=str(repo_root),
        report_md=str(out_path),
        report_json=str(json_out),
        files_scanned=len(metas),
        by_language=results.get("by_language", {}),
        top_issues=len(results.get("findings_scored", [])),
    )
