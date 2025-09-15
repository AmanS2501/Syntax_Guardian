from __future__ import annotations
from pathlib import Path
from typing import Iterable, Dict, List, Any, Mapping

from cqia.ingestion.walker import FileMeta
from cqia.analysis.severity import ScoredFinding
from cqia.analysis.detectors.complexity import ComplexityFinding
from cqia.analysis.detectors.duplication import DupFinding
from cqia.analysis.detectors.security import SecFinding
from cqia.analysis.detectors.performance import PerfFinding
from cqia.analysis.detectors.testing_docs import DocFinding, TestGapFinding


# ---------- Safe casting helpers ----------

def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        try:
            if isinstance(x, (list, tuple)):
                if len(x) > 1:
                    return float(x[1])
                if len(x) == 1:
                    return float(x[0])
            return float(default)
        except Exception:
            return float(default)

def _as_int(x: Any, default: int = 0) -> int:
    try:
        if isinstance(x, (list, tuple)):
            if len(x) > 1:
                return int(_f(x[1], 0.0))
            if len(x) == 1:
                return int(_f(x[0], 0.0))
            return int(default)
        return int(_f(x, float(default)))
    except Exception:
        return int(default)

def _i(x: Any, default: int = 0) -> int:
    try:
        return int(_f(x, float(default)))
    except Exception:
        return int(default)

def _get(obj: Any, key: str, default: Any = None) -> Any:
    try:
        return getattr(obj, key)
    except Exception:
        if isinstance(obj, Mapping):
            return obj.get(key, default)
        return default


# ---------- TOC and basic report ----------

def _toc() -> str:
    return (
        "\n- [Summary](#summary)\n"
        "- [Top issues](#top-issues)\n"
        "- [Per-category](#per-category)\n"
        "- [Issue details](#issue-details)\n"
        "- [Dependencies](#dependencies)\n"
    )

def write_basic_report(files: Iterable[FileMeta], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "report.md"

    files_list = list(files)
    lang_counts: Dict[str, int] = {}
    for f in files_list:
        lang = getattr(f, "language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    total = len(files_list)
    py = int(lang_counts.get("python", 0))
    js = int(lang_counts.get("javascript", 0))
    ts = int(lang_counts.get("typescript", 0))

    lines: List[str] = []
    lines.append("# Code Quality Report\n")
    lines.append(_toc())
    lines.append("\n## Summary\n")
    lines.append(f"- Files scanned: {total}\n")
    lines.append(f"- Python: {py}  |  JavaScript: {js}  |  TypeScript: {ts}\n")
    lines.append("\n### File listing\n")
    for f in files_list:
        path = getattr(f, "path", "")
        lang = getattr(f, "language", "unknown")
        ln = int(getattr(f, "lines", 0) or 0)
        lines.append(f"- {path} ({lang}, {ln} lines)\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    return out_path


# ---------- Top issues and summaries ----------

def append_top_issues(out_path: Path, scored: List[ScoredFinding], max_rows: int = 10) -> None:
    lines: List[str] = []
    lines.append("\n## Top issues\n")
    if not scored:
        lines.append("- No issues found.\n")
    else:
        lines.append("| Severity | Score | Category | Location | Title |\n")
        lines.append("|---|---:|---|---|---|\n")
        top = sorted(scored, key=lambda s: _f(getattr(s, "score", 0.0), 0.0), reverse=True)[:max_rows]
        for s in top:
            sev = getattr(s, "severity", "P3")
            sc = _f(getattr(s, "score", 0.0), 0.0)
            cat = getattr(s, "category", "issue")
            file_ = getattr(s, "file", "")
            a = int(getattr(s, "start_line", 1) or 1)
            b = int(getattr(s, "end_line", a) or a)
            title = getattr(s, "title", getattr(s, "why", "Issue"))
            loc = f"{file_}:{a}-{b}"
            lines.append(f"| {sev} | {sc:.2f} | {cat} | {loc} | {title} |\n")
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))

def append_per_category_summary(out_path: Path, scored: List[ScoredFinding], top_n: int = 5) -> None:
    groups: Dict[str, List[ScoredFinding]] = {}
    for s in scored:
        groups.setdefault(getattr(s, "category", "other"), []).append(s)
    for k in groups:
        groups[k].sort(key=lambda x: (-_f(getattr(x, "score", 0.0), 0.0), getattr(x, "file", "")))
    lines: List[str] = []
    lines.append("\n## Per-category\n")
    if not groups:
        lines.append("- No issues found.\n")
    else:
        for cat, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            lines.append(f"\n### {cat.capitalize()} ({len(items)})\n")
            for s in items[:top_n]:
                sev = getattr(s, "severity", "P3")
                title = getattr(s, "title", getattr(s, "why", "Issue"))
                file_ = getattr(s, "file", "")
                a = int(getattr(s, "start_line", 1) or 1)
                b = int(getattr(s, "end_line", a) or a)
                sc = _f(getattr(s, "score", 0.0), 0.0)
                loc = f"{file_}:{a}-{b}"
                lines.append(f"- [{sev}] {title} — {loc} — score {sc:.2f}\n")
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))

def append_issue_details(out_path: Path, scored: List[ScoredFinding]) -> None:
    lines: List[str] = []
    lines.append("\n## Issue details\n")
    if not scored:
        lines.append("- No issues found.\n")
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write("".join(lines))
        return

    grouped: Dict[str, List[ScoredFinding]] = {}
    for s in scored:
        grouped.setdefault(getattr(s, "category", "other"), []).append(s)

    for cat, items in grouped.items():
        lines.append(f"\n### {cat.capitalize()}\n")
        items_sorted = sorted(items, key=lambda x: _f(getattr(x, "score", 0.0), 0.0), reverse=True)[:50]
        for s in items_sorted:
            sev = getattr(s, "severity", "P3")
            title = getattr(s, "title", getattr(s, "why", "Issue"))
            why = getattr(s, "why", "")
            fix = getattr(s, "fix", "")
            file_ = getattr(s, "file", "")
            a = int(getattr(s, "start_line", 1) or 1)
            b = int(getattr(s, "end_line", a) or a)
            sc = _f(getattr(s, "score", 0.0), 0.0)
            lines.append(f"- [{sev} • {sc:.2f}] {title}\n")
            lines.append(f"  - Where: {file_}:{a}-{b}\n")
            lines.append(f"  - Why: {why}\n")
            lines.append(f"  - Fix: {fix}\n")

    with out_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))


# ---------- Raw findings ----------

def append_findings(out_path: Path, findings: dict) -> None:
    lines: List[str] = []
    lines.append("\n## Findings\n")

    # Security
    sec: List[SecFinding] = findings.get("security", []) or []
    lines.append(f"\n### Security ({len(sec)})\n")
    for f in sec:
        a = _as_int(getattr(f, "start_line", 1), 1)
        b = _as_int(getattr(f, "end_line", a), a)
        lines.append(f"- {str(getattr(f,'file',''))}:{a}-{b} — {getattr(f,'message','')}\n")

    # Complexity
    comp: List[ComplexityFinding] = findings.get("complexity", []) or []
    lines.append(f"\n### Complexity ({len(comp)})\n")
    for f in comp:
        a = _as_int(getattr(f, "start_line", 1), 1)
        b = _as_int(getattr(f, "end_line", a), a)
        lines.append(f"- {str(getattr(f,'file',''))}:{a}-{b} — {getattr(f,'message','')}\n")

    # Duplication
    dup: List[DupFinding] = findings.get("duplication", []) or []
    lines.append(f"\n### Duplication ({len(dup)})\n")
    for f in dup:
        fp = getattr(f, "files", ())
        f1 = ""; f2 = ""
        if isinstance(fp, (tuple, list)):
            if len(fp) >= 1:
                f1 = str(fp[0])
            if len(fp) >= 2:
                f2 = str(fp[1])
        pair = f"{f1} vs {f2}" if f2 else (f1 or "<unknown>")
        msg = str(getattr(f, "message", "duplicate"))
        lines.append(f"- {pair} — {msg}\n")

    # Performance
    perf: List[PerfFinding] = findings.get("performance", []) or []
    lines.append(f"\n### Performance ({len(perf)})\n")
    for f in perf:
        a = _as_int(getattr(f, "start_line", 1), 1)
        b = _as_int(getattr(f, "end_line", a), a)
        lines.append(f"- {str(getattr(f,'file',''))}:{a}-{b} — {getattr(f,'message','')} — Hint: {getattr(f,'hint','')}\n")

    # Documentation
    docs: List[DocFinding] = findings.get("documentation", []) or []
    lines.append(f"\n### Documentation ({len(docs)})\n")
    for f in docs:
        a = _as_int(getattr(f, "start_line", 1), 1)
        b = _as_int(getattr(f, "end_line", a), a)
        lines.append(f"- {str(getattr(f,'file',''))}:{a}-{b} — {getattr(f,'message','')}\n")

    # Testing
    tests: List[TestGapFinding] = findings.get("testing", []) or []
    lines.append(f"\n### Testing ({len(tests)})\n")
    for f in tests:
        exp = getattr(f, "expected_test", "tests/test_<name>.py")
        hint = getattr(f, "hint", "Create a test file")
        lines.append(f"- {str(getattr(f,'file',''))} — Missing mapped test ⇒ {exp} — Hint: {hint}\n")

    with out_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))



# ---------- Dependencies ----------

def append_dependencies(out_path: Path, metrics: dict) -> None:
    fan_in = metrics.get("fan_in", {}) or {}
    top_fan_in = metrics.get("top_fan_in", []) or []
    top_fan_out = metrics.get("top_fan_out", []) or []
    cycles = metrics.get("cycles", []) or []

    lines: List[str] = []
    lines.append("\n## Dependencies\n")
    lines.append(f"- Nodes: {len(fan_in)}\n")
    lines.append("- Top fan-in:\n")
    for item in list(top_fan_in)[:5]:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            n, v = item[0], item[1]
        else:
            n, v = str(item), 0
        lines.append(f"  - {str(n)}: {_as_int(v)}\n")
    lines.append("- Top fan-out:\n")
    for item in list(top_fan_out)[:5]:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            n, v = item[0], item[1]
        else:
            n, v = str(item), 0
        lines.append(f"  - {str(n)}: {_as_int(v)}\n")
    if cycles:
        lines.append(f"- Cycles detected: {len(cycles)}\n")
        for c in list(cycles)[:5]:
            lines.append(f"  - {' -> '.join([str(x) for x in c])}\n")
    else:
        lines.append("- Cycles detected: 0\n")

    with out_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))

def append_dependency_outline(out_path: Path, metrics: dict, hotspots: List[tuple[str, float, int, float]]) -> None:
    fan_in = metrics.get("fan_in", {}) or {}
    top_fan_in = metrics.get("top_fan_in", []) or []
    top_fan_out = metrics.get("top_fan_out", []) or []
    cycles = metrics.get("cycles", []) or []

    lines: List[str] = []
    lines.append("\n## Dependency outline\n")
    lines.append("- Graph summary:\n")
    lines.append(f"  - Nodes: {len(fan_in)}\n")
    try:
        edge_count = sum(_as_int(v) for v in fan_in.values())
    except Exception:
        edge_count = 0
    lines.append(f"  - Edges: {edge_count}\n")
    lines.append("- Top fan-in modules:\n")
    for item in list(top_fan_in)[:5]:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            n, v = item[0], item[1]
        else:
            n, v = str(item), 0
        lines.append(f"  - {n}: {_as_int(v)}\n")
    lines.append("- Top fan-out modules:\n")
    for item in list(top_fan_out)[:5]:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            n, v = item[0], item[1]
        else:
            n, v = str(item), 0
        lines.append(f"  - {n}: {_as_int(v)}\n")
    if cycles:
        lines.append(f"- Cycles: {len(cycles)}\n")
        for c in list(cycles)[:5]:
            lines.append(f"  - {' -> '.join([str(x) for x in c])}\n")
    else:
        lines.append("- Cycles: 0\n")
    if hotspots:
        lines.append("- Hotspots (fan-in × complexity):\n")
        for path_str, score, fi, comp_sum in hotspots[:8]:
            lines.append(f"  - {path_str} — score {float(_f(score, 0.0)):.2f} (fan-in {_as_int(fi)}, complexity {_as_int(comp_sum)})\n")
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))
