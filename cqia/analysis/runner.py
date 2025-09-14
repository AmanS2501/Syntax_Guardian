
from __future__ import annotations

import json
import typing as t
from dataclasses import dataclass
from pathlib import Path
import networkx as nx

from cqia.ingestion.walker import FileMeta, walk_repo
from cqia.parsing.ir import ModuleIR, FunctionIR
from cqia.parsing.python_parser import parse_python
from cqia.parsing.ts_parser import parse_js_ts
from cqia.analysis.detectors.complexity import detect_complexity, ComplexityFinding
from cqia.analysis.detectors.testing_docs import run_testing_and_docs, DocFinding, TestGapFinding
from cqia.analysis.detectors.duplication import detect_duplication, DupFinding
from cqia.analysis.detectors.security import scan_python_security, scan_js_security, SecFinding
from cqia.analysis.detectors.performance import detect_performance, PerfFinding
from cqia.analysis.dependency_graph import DepEdge, build_dep_graph
from cqia.analysis.severity import (
    DEFAULT_WEIGHTS, ScoredFinding,
    score_security, score_complexity, score_duplication, score_performance_base,
    score_documentation_base, score_testing_base, pick_severity, explain, fix_text,
)

Number = t.Union[int, float]

def _fnum(x: t.Any, default: float = 0.0) -> float:
    try: return float(x)
    except Exception: return float(default)

def _inum(x: t.Any, default: int = 0) -> int:
    try: return int(x)
    except Exception:
        try: return int(float(x))
        except Exception: return int(default)

def _norm(val: Number, max_val: Number) -> float:
    mv = _fnum(max_val, 1.0)
    if mv == 0.0: return 0.0
    return _fnum(val, 0.0) / mv

def _detect_language(path: Path) -> str:
    p = str(path).lower()
    if p.endswith(".py"): return "python"
    if p.endswith(".ts"): return "typescript"
    if p.endswith(".js"): return "javascript"
    return "unknown"

def _parse_modules(root: Path, files: list[Path]) -> list[ModuleIR]:
    modules: list[ModuleIR] = []
    for rel in files:
        fpath = root / rel
        try: text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception: text = ""
        lang = _detect_language(fpath)
        if lang == "python":
            modules.append(parse_python(rel, text))
        elif lang in {"javascript", "typescript"}:
            modules.append(parse_js_ts(rel, text, lang))
        else:
            modules.append(ModuleIR(path=rel, lang="unknown", functions=[]))
    return modules

@dataclass
class DepMetricsCompat:
    fan_in: dict[str, int]
    fan_out: dict[str, int]
    cycles: list[list[str]]
    top_fan_in: list[tuple[str, int]]
    top_fan_out: list[tuple[str, int]]

def _safe_read_imports(root: Path, path: Path, language: str) -> list[str]:
    try:
        from cqia.parsing.imports import read_imports
        return [str(x) for x in read_imports(path, language, root)]
    except Exception:
        return []

def analyze_repository(
    root: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    max_bytes: int | None = None,
    rules: dict | None = None,
) -> tuple[
    list[ModuleIR],
    list[FunctionIR],
    list[ComplexityFinding],
    list[DocFinding],
    list[SecFinding],
    list[TestGapFinding],
    list[DupFinding],
    list[PerfFinding],
    list[DepEdge],
    DepMetricsCompat,
    nx.DiGraph,
]:
    include = include or ["**/*.py", "**/*.js", "**/*.ts"]
    exclude = exclude or [".git/**", "**/.git/**", "**/.venv/**", "**/venv/**", "**/__pycache__/**", "**/node_modules/**"]
    max_bytes = int(max_bytes or 2_000_000)

    metas: list[FileMeta] = walk_repo(root, include, exclude, max_bytes, follow_symlinks=False)
    file_paths = [m.path for m in metas]

    modules = _parse_modules(root, file_paths)

    # Flatten functions across languages
    all_functions: list[FunctionIR] = []
    for m in modules:
        all_functions.extend(m.functions)

    # Security
    sec_findings: list[SecFinding] = []
    for m in modules:
        fpath = root / m.path
        try: text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception: text = ""
        lang = _detect_language(fpath)
        if lang == "python":
            sec_findings.extend(scan_python_security(m, text))
        elif lang in {"javascript", "typescript"}:
            sec_findings.extend(scan_js_security(m, text))

    # Thresholds
    cx = (rules or {}).get("complexity", {}) if isinstance(rules, dict) else {}
    warn_at = cx.get("warn_at", 10)

    # Core findings
    try: comp_findings = detect_complexity(all_functions, warn_at=warn_at)
    except Exception: comp_findings = []

    dup_cfg = (rules or {}).get("duplication", {}) if isinstance(rules, dict) else {}
    k_shingle = dup_cfg.get("k_shingle", 7)
    similarity_threshold = dup_cfg.get("similarity_threshold", 0.90)
    try: dup_findings = detect_duplication(all_functions, k=k_shingle, threshold=similarity_threshold)
    except Exception: dup_findings = []

    try: docs, gaps = run_testing_and_docs(root, modules)
    except Exception: docs, gaps = [], []

    # Performance on Python functions
    try: perf_findings = detect_performance(all_functions, root)
    except Exception: perf_findings = []

    # Dependencies
    dep_edges: list[DepEdge] = []
    for m in metas:
        for dst in (d for d in _safe_read_imports(root, m.path, m.language)):
            src = str(m.path.stem)
            dep_edges.append(DepEdge(src=src, dst=str(dst)))
    G, dep_metrics_native = build_dep_graph(dep_edges)
    dep_metrics = DepMetricsCompat(
        fan_in={k: int(v) for k, v in dep_metrics_native.fan_in.items()},
        fan_out={k: int(v) for k, v in dep_metrics_native.fan_out.items()},
        cycles=[[str(x) for x in cyc] for cyc in dep_metrics_native.cycles],
        top_fan_in=[(str(n), int(v)) for (n, v) in dep_metrics_native.top_fan_in],
        top_fan_out=[(str(n), int(v)) for (n, v) in dep_metrics_native.top_fan_out],
    )

    return (modules, all_functions, comp_findings, docs, sec_findings, gaps, dup_findings, perf_findings, dep_edges, dep_metrics, G)

def _score_all_findings(
    comp: list[ComplexityFinding],
    docs: list[DocFinding],
    sec: list[SecFinding],
    gaps: list[TestGapFinding],
    dups: list[DupFinding],
    perf: list[PerfFinding],
    warn_at: int | None,
) -> tuple[list[ScoredFinding], list[dict]]:
    scored: list[ScoredFinding] = []
    jsonable: list[dict] = []

    def _push(cat: str, fid: str, file: str, s: int, e: int, score_val: float, title: str, why: str, fix: str, extra: dict | None = None):
        sev = pick_severity(cat, score_val)
        sf = ScoredFinding(id=fid, category=cat, severity=sev, score=float(score_val), title=title, file=file, start_line=int(s), end_line=int(e), why=why, fix=fix, extra=extra or {})
        scored.append(sf)
        jsonable.append({
            "id": fid, "category": cat, "severity": sev, "score": float(score_val),
            "title": title, "file": file, "start_line": int(s), "end_line": int(e),
            "hint": fix, "extra": extra or {}
        })

    w = DEFAULT_WEIGHTS

    for f in sec:
        base = score_security(w["security"])
        _push("security", f.id, f.file, f.start_line, f.end_line, base, f.message, explain("security"), fix_text("security", None), {})

    for f in comp:
        base = score_complexity(float(getattr(f, "value", 0.0)), w["complexity"], float(warn_at or f.threshold))
        _push("complexity", f.id, f.file, f.start_line, f.end_line, base, f.message, explain("complexity"), fix_text("complexity", None), {"value": float(getattr(f, "value", 0.0)), "threshold": float(getattr(f, "threshold", 0.0))})

    for f in dups:
        base = score_duplication(float(getattr(f, "similarity", 0.0)), w["duplication"])
        extra = {"other_file": (f.files[1] if isinstance(f.files, (list, tuple)) and len(f.files) > 1 else "")}
        file_a = f.files if isinstance(f.files, (list, tuple)) and len(f.files) > 0 else ""
        s_a, e_a = f.lines if isinstance(f.lines, (list, tuple)) and len(f.lines) > 0 else (1, 1)
        _push("duplication", f.id, file_a, s_a, e_a, base, f.message, explain("duplication"), fix_text("duplication", extra), extra)

    for f in perf:
        base = score_performance_base(w["performance"])
        _push("performance", f.id, f.file, f.start_line, f.end_line, base, f.message, explain("performance"), fix_text("performance", {"kind": f.kind}), {"kind": f.kind})

    for f in docs:
        base = score_documentation_base(w["documentation"])
        _push("documentation", f.id, f.file, f.start_line, f.end_line, base, f.message, explain("documentation"), fix_text("documentation", None), {"kind": f.kind})

    for f in gaps:
        base = score_testing_base(w["testing"])
        _push("testing", f.id, f.file, 1, 1, base, f.message, explain("testing"), fix_text("testing", {"expected_test": f.expected_test}), {"expected_test": f.expected_test})

    return scored, jsonable

def run_analysis(
    root: t.Union[str, Path],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    rules: dict | None = None,
    max_bytes: int | None = None,
    warn_at: int | None = None,
    p1_cutoff: int | None = None,
    p0_cutoff: int | None = None,
    **kwargs: t.Any,
) -> dict:
    root = Path(root).resolve()

    if isinstance(rules, dict):
        cx = rules.get("complexity", {})
        if warn_at is None: warn_at = cx.get("warn_at")
        if p1_cutoff is None: p1_cutoff = cx.get("p1_cutoff")
        if p0_cutoff is None: p0_cutoff = cx.get("p0_cutoff")

    modules, all_functions, comp, docs, sec_findings, gaps, dups, perf_findings, dep_edges, dep_metrics, dep_graph = analyze_repository(
        root, include=include, exclude=exclude, max_bytes=max_bytes, rules=rules
    )

    # Aggregations for hotspots
    comp_map: dict[str, float] = {}
    for f in comp:
        comp_map.setdefault(getattr(f, "file", ""), 0.0)
        comp_map[getattr(f, "file", "")] += _fnum(getattr(f, "value", 0.0), 0.0)

    max_comp = max(comp_map.values(), default=0.0)
    fan_in = dep_metrics.fan_in
    max_fi = max(fan_in.values(), default=0)

    hotspots: list[tuple[str, float, int, float]] = []
    for path_str, comp_sum in comp_map.items():
        key = Path(path_str).stem
        fi_val = _inum(fan_in.get(key, 0), 0)
        comp_val = _fnum(comp_sum, 0.0)
        score_val = _norm(fi_val, max_fi or 1) * _norm(comp_val, max_comp or 1)
        hotspots.append((str(path_str), float(score_val), int(fi_val), float(comp_val)))

    hotspots.sort(key=lambda r: (-_fnum(r[1], 0.0), -_inum(r[2], 0), -_fnum(r[3], 0.0), str(r)))

    # Scoring
    scored, findings_json = _score_all_findings(
        comp, docs, sec_findings, gaps, dups, perf_findings, warn_at or 10
    )

    report: dict = {
        "summary": {
            "files_analyzed": len({m.path for m in modules}),
            "functions_analyzed": len(all_functions),
            "complexity_findings": len(comp),
            "documentation_findings": len(docs),
            "security_findings": len(sec_findings),
            "test_gap_findings": len(gaps),
            "duplication_findings": len(dups),
            "performance_findings": len(perf_findings),
        },
        "by_language": {
            "python": sum(1 for m in modules if m.lang == "python"),
            "javascript": sum(1 for m in modules if m.lang == "javascript"),
            "typescript": sum(1 for m in modules if m.lang == "typescript"),
        },
        "hotspots": [
            {"path": p, "score": s, "fan_in": fi, "complexity_sum": cc}
            for (p, s, fi, cc) in hotspots
        ],
        "findings_scored": [
            {
                "id": s.id, "category": s.category, "severity": s.severity, "score": s.score,
                "title": s.title, "file": s.file, "start_line": s.start_line, "end_line": s.end_line,
                "why": s.why, "fix": s.fix, "extra": s.extra or {}
            } for s in scored
        ],
        "findings_json": findings_json,
        "findings_raw": {
            "complexity": comp,
            "documentation": docs,
            "security": sec_findings,
            "testing": gaps,
            "duplication": dups,
            "performance": perf_findings,
        },
        "dep_graph": dep_graph,
        "dep_metrics": {
            "fan_in": dep_metrics.fan_in,
            "fan_out": dep_metrics.fan_out,
            "cycles": dep_metrics.cycles,
            "top_fan_in": dep_metrics.top_fan_in,
            "top_fan_out": dep_metrics.top_fan_out,
        },
        "dependencies": {
            "edges": [e.__dict__ for e in dep_edges],
            "metrics": {
                "fan_in": dep_metrics.fan_in,
                "fan_out": dep_metrics.fan_out,
                "cycles": dep_metrics.cycles,
                "top_fan_in": dep_metrics.top_fan_in,
                "top_fan_out": dep_metrics.top_fan_out,
            },
        },
        "thresholds": {
            "warn_at": warn_at,
            "p1_cutoff": p1_cutoff,
            "p0_cutoff": p0_cutoff,
            "max_bytes": max_bytes,
        },
    }
    return report
