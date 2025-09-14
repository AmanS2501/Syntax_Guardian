# from __future__ import annotations
# from pathlib import Path
# from typing import Iterable, Sequence, Mapping, Any, List

# # Optional typed imports (for hints only)
# from cqia.analysis.detectors.testing_docs import DocFinding, TestGapFinding
# from cqia.analysis.detectors.complexity import ComplexityFinding
# from cqia.analysis.detectors.duplication import DupFinding
# from cqia.analysis.detectors.performance import PerfFinding
# from cqia.analysis.detectors.security import SecFinding

# def _f(x, default: float = 0.0) -> float:
#     try:
#         return float(x)
#     except Exception:
#         try:
#             if isinstance(x, (list, tuple)) and len(x) > 1:
#                 return float(x[1])
#             return float(default)
#         except Exception:
#             return float(default)


# def _as_int(x) -> int:
#     if isinstance(x, (list, tuple)):
#         if len(x) > 1:
#             return int(_f(x[1], 0))
#         if len(x) == 1:
#             return int(_f(x, 0))
#         return 0
#     return int(_f(x, 0.0))

# def _i(x: Any, default: int = 0) -> int:
#     try:
#         return int(_f(x, default))
#     except Exception:
#         return int(default)

# def _get(obj: Any, key: str, default: Any = None) -> Any:
#     try:
#         return getattr(obj, key)
#     except Exception:
#         if isinstance(obj, Mapping):
#             return obj.get(key, default)
#         return default

# def _int(obj: Any, key: str, default: int = 1) -> int:
#     return _i(_get(obj, key, default), default)

# def _str(obj: Any, key: str, default: str = "") -> str:
#     try:
#         return str(_get(obj, key, default))
#     except Exception:
#         return str(default)

# def write_basic_report(files: Sequence, out_dir: Path) -> Path:
#     out_dir.mkdir(parents=True, exist_ok=True)
#     out_path = out_dir / "report.md"
#     lines: List[str] = []
#     lines.append("# Code Quality Report\n\n")
#     lines.append("- [Summary](#summary)\n- [Top issues](#top-issues)\n- [Per-category](#per-category)\n- [Issue details](#issue-details)\n- [Dependencies](#dependencies)\n\n")

#     # Summary
#     lang_counts: dict[str, int] = {}
#     for f in files:
#         lang = _str(f, "language", "unknown")
#         lang_counts[lang] = lang_counts.get(lang, 0) + 1
#     lines.append("## Summary\n")
#     lines.append(f"- Files scanned: {len(files)}\n")
#     py = lang_counts.get("python", 0); js = lang_counts.get("javascript", 0); ts = lang_counts.get("typescript", 0)
#     lines.append(f"- Python: {py}  |  JavaScript: {js}  |  TypeScript: {ts}\n\n")

#     lines.append("### File listing\n")
#     for f in files:
#         path = _str(f, "path")
#         lang = _str(f, "language", "unknown")
#         ln = _int(f, "lines", 0)
#         lines.append(f"- {path} ({lang}, {ln} lines)\n")

#     out_path.write_text("".join(lines), encoding="utf-8")
#     return out_path

# def append_top_issues(out_path: Path, findings_scored: Sequence[Any]) -> None:
#     lines: List[str] = []
#     lines.append("\n## Top issues\n")
#     if not findings_scored:
#         lines.append("- No issues found.\n")
#         with out_path.open("a", encoding="utf-8") as fh:
#             fh.write("".join(lines))
#         return

#     items = sorted(findings_scored, key=lambda s: float(_get(s, "score", 0.0)), reverse=True)[:10]
#     for s in items:
#         cat = _str(s, "category", "issue")
#         sev = _str(s, "severity", "P3")
#         title = _str(s, "title", _str(s, "why", "Issue"))
#         file_ = _str(s, "file", "")
#         a = _int(s, "start_line", 1); b = _int(s, "end_line", a)
#         sc = _f(_get(s, "score", 0.0), 0.0)
#         lines.append(f"- [{sev}] {cat}: {title} — {file_}:{a}-{b} (score {sc:.2f})\n")
#     with out_path.open("a", encoding="utf-8") as fh:
#         fh.write("".join(lines))

# def append_per_category_summary(out_path: Path, findings_scored: Sequence[Any]) -> None:
#     lines: List[str] = []
#     lines.append("\n## Per-category\n")
#     if not findings_scored:
#         lines.append("- No issues found.\n")
#         with out_path.open("a", encoding="utf-8") as fh:
#             fh.write("".join(lines))
#         return
#     counts: dict[str, int] = {}
#     for s in findings_scored:
#         cat = _str(s, "category", "other")
#         counts[cat] = counts.get(cat, 0) + 1
#     for cat, n in sorted(counts.items(), key=lambda x: x):
#         lines.append(f"- {cat}: {n}\n")
#     with out_path.open("a", encoding="utf-8") as fh:
#         fh.write("".join(lines))

# def append_issue_details(out_path: Path, findings_scored: Sequence[Any]) -> None:
#     lines: List[str] = []
#     lines.append("\n## Issue details\n")
#     if not findings_scored:
#         lines.append("- No issues found.\n")
#         with out_path.open("a", encoding="utf-8") as fh:
#             fh.write("".join(lines))
#         return
#     grouped: dict[str, list[Any]] = {}
#     for s in findings_scored:
#         grouped.setdefault(_str(s, "category", "other"), []).append(s)
#     for cat, items in grouped.items():
#         lines.append(f"\n### {cat.capitalize()}\n")
#         for s in sorted(items, key=lambda x: float(_get(x, "score", 0.0)), reverse=True)[:50]:
#             sev = _str(s, "severity", "P3")
#             title = _str(s, "title", _str(s, "why", "Issue"))
#             why = _str(s, "why", "")
#             fix = _str(s, "fix", "")
#             file_ = _str(s, "file", "")
#             a = _int(s, "start_line", 1); b = _int(s, "end_line", a)
#             sc = _f(_get(s, "score", 0.0), 0.0)
#             lines.append(f"- [{sev} • {sc:.2f}] {title}\n  - Where: {file_}:{a}-{b}\n  - Why: {why}\n  - Fix: {fix}\n")
#     with out_path.open("a", encoding="utf-8") as fh:
#         fh.write("".join(lines))

# def append_findings(out_path: Path, findings: dict) -> None:
#     lines = []
#     lines.append("\n## Findings\n")

#     sec = findings.get("security", [])
#     lines.append(f"\n### Security ({len(sec)})\n")
#     for f in sec:
#         lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')}\n")

#     comp = findings.get("complexity", [])
#     lines.append(f"\n### Complexity ({len(comp)})\n")
#     for f in comp:
#         lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')}\n")

#     dup = findings.get("duplication", [])
#     lines.append(f"\n### Duplication ({len(dup)})\n")
#     for f in dup:
#         fp = getattr(f, "files", ())
#         f1 = ""; f2 = ""
#         if isinstance(fp, (tuple, list)):
#             if len(fp) >= 1:
#                 f1 = str(fp)
#             if len(fp) >= 2:
#                 f2 = str(fp[1])
#         pair = f"{f1} vs {f2}" if f2 else (f1 or "<unknown>")
#         msg = str(getattr(f, "message", "duplicate"))
#         lines.append(f"- {pair} — {msg}\n")

#     perf = findings.get("performance", [])
#     lines.append(f"\n### Performance ({len(perf)})\n")
#     for f in perf:
#         lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')} — Hint: {getattr(f,'hint','')}\n")

#     docs = findings.get("documentation", [])
#     lines.append(f"\n### Documentation ({len(docs)})\n")
#     for f in docs:
#         lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')}\n")

#     tests = findings.get("testing", [])
#     lines.append(f"\n### Testing ({len(tests)})\n")
#     for f in tests:
#         exp = getattr(f, 'expected_test', 'tests/test_<name>.py')
#         hint = getattr(f, 'hint', 'Create a test file')
#         lines.append(f"- {str(getattr(f,'file',''))} — Missing mapped test ⇒ {exp} — Hint: {hint}\n")

#     with out_path.open("a", encoding="utf-8") as fh:
#         fh.write("".join(lines))


# def append_dependencies(out_path: Path, metrics: dict) -> None:
#     fan_in = metrics.get("fan_in", {}) or {}
#     top_fan_in = metrics.get("top_fan_in", []) or []
#     top_fan_out = metrics.get("top_fan_out", []) or []
#     cycles = metrics.get("cycles", []) or []

#     lines = []
#     lines.append("\n## Dependencies\n")
#     lines.append(f"- Nodes: {len(fan_in)}\n")
#     lines.append("- Top fan-in:\n")
#     for n, v in list(top_fan_in)[:5]:
#         lines.append(f"  - {str(n)}: {_as_int(v)}\n")
#     lines.append("- Top fan-out:\n")
#     for n, v in list(top_fan_out)[:5]:
#         lines.append(f"  - {str(n)}: {_as_int(v)}\n")
#     if cycles:
#         lines.append(f"- Cycles detected: {len(cycles)}\n")
#         for c in list(cycles)[:5]:
#             lines.append(f"  - {' -> '.join([str(x) for x in c])}\n")
#     else:
#         lines.append("- Cycles detected: 0\n")

#     with out_path.open("a", encoding="utf-8") as fh:
#         fh.write("".join(lines))

# def append_dependency_outline(out_path: Path, metrics: dict, hotspots: list[tuple[str, float, int, float]]) -> None:
#     fan_in = metrics.get("fan_in", {}) or {}
#     fan_out = metrics.get("fan_out", {}) or {}
#     cycles = metrics.get("cycles", []) or []
#     top_fan_in = metrics.get("top_fan_in", []) or []
#     top_fan_out = metrics.get("top_fan_out", []) or []

#     lines = []
#     lines.append("\n## Dependency outline\n")
#     lines.append("- Graph summary:\n")
#     lines.append(f"  - Nodes: {len(fan_in)}\n")
#     # Sum of in-degree values; handle tuple/list values defensively
#     try:
#         edge_count = sum(_as_int(v) for v in fan_in.values())
#     except Exception:
#         edge_count = 0
#     lines.append(f"  - Edges: {edge_count}\n")
#     lines.append("- Top fan-in modules:\n")
#     for n, v in list(top_fan_in)[:5]:
#         lines.append(f"  - {n}: {_as_int(v)}\n")
#     lines.append("- Top fan-out modules:\n")
#     for n, v in list(top_fan_out)[:5]:
#         lines.append(f"  - {n}: {_as_int(v)}\n")
#     if cycles:
#         lines.append(f"- Cycles: {len(cycles)}\n")
#         for c in list(cycles)[:5]:
#             lines.append(f"  - {' -> '.join([str(x) for x in c])}\n")
#     else:
#         lines.append("- Cycles: 0\n")
#     if hotspots:
#         lines.append("- Hotspots (fan-in × complexity):\n")
#         for path_str, score, fi, comp_sum in hotspots[:8]:
#             lines.append(f"  - {path_str} — score {float(score):.2f} (fan-in {int(fi)}, complexity {int(comp_sum)})\n")
#     with out_path.open("a", encoding="utf-8") as fh:
#         fh.write("".join(lines))


from __future__ import annotations
from pathlib import Path
from typing import Iterable, Dict, List, Any, Mapping, Sequence

from cqia.ingestion.walker import FileMeta
from cqia.analysis.severity import ScoredFinding
from cqia.analysis.detectors.complexity import ComplexityFinding
from cqia.analysis.detectors.duplication import DupFinding
from cqia.analysis.detectors.security import SecFinding
from cqia.analysis.detectors.performance import PerfFinding
from cqia.analysis.detectors.testing_docs import DocFinding, TestGapFinding


# ----------------------
# Safe casting utilities
# ----------------------

def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        try:
            # Handle pair-like shapes: (name, value) or [name, value]
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

def _int(obj: Any, key: str, default: int = 1) -> int:
    return _i(_get(obj, key, default), default)

def _str(obj: Any, key: str, default: str = "") -> str:
    try:
        return str(_get(obj, key, default))
    except Exception:
        return str(default)


# ----------------------
# TOC and basic sections
# ----------------------

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

    # Count by language
    lang_counts: Dict[str, int] = {}
    files_list = list(files)
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


# ----------------------
# Findings summaries
# ----------------------

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


# ----------------------
# Raw findings section
# ----------------------

def append_findings(out_path: Path, findings: dict) -> None:
    lines: List[str] = []
    lines.append("\n## Findings\n")

    # Security
    sec: List[SecFinding] = findings.get("security", []) or []
    lines.append(f"\n### Security ({len(sec)})\n")
    for f in sec:
        lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')}\n")

    # Complexity
    comp: List[ComplexityFinding] = findings.get("complexity", []) or []
    lines.append(f"\n### Complexity ({len(comp)})\n")
    for f in comp:
        lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')}\n")

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
        lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')} — Hint: {getattr(f,'hint','')}\n")

    # Documentation
    docs: List[DocFinding] = findings.get("documentation", []) or []
    lines.append(f"\n### Documentation ({len(docs)})\n")
    for f in docs:
        lines.append(f"- {str(getattr(f,'file',''))}:{int(getattr(f,'start_line',1))}-{int(getattr(f,'end_line',1))} — {getattr(f,'message','')}\n")

    # Testing
    tests: List[TestGapFinding] = findings.get("testing", []) or []
    lines.append(f"\n### Testing ({len(tests)})\n")
    for f in tests:
        exp = getattr(f, 'expected_test', 'tests/test_<name>.py')
        hint = getattr(f, 'hint', 'Create a test file')
        lines.append(f"- {str(getattr(f,'file',''))} — Missing mapped test ⇒ {exp} — Hint: {hint}\n")

    with out_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(lines))


# ----------------------
# Dependencies sections
# ----------------------

def append_dependencies(out_path: Path, metrics: dict) -> None:
    fan_in = metrics.get("fan_in", {}) or {}
    top_fan_in = metrics.get("top_fan_in", []) or []
    top_fan_out = metrics.get("top_fan_out", []) or []
    cycles = metrics.get("cycles", []) or []

    lines: List[str] = []
    lines.append("\n## Dependencies\n")
    lines.append(f"- Nodes: {len(fan_in)}\n")
    lines.append("- Top fan-in:\n")
    for n, v in list(top_fan_in)[:5]:
        lines.append(f"  - {str(n)}: {_as_int(v)}\n")
    lines.append("- Top fan-out:\n")
    for n, v in list(top_fan_out)[:5]:
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
    fan_out = metrics.get("fan_out", {}) or {}
    cycles = metrics.get("cycles", []) or []
    top_fan_in = metrics.get("top_fan_in", []) or []
    top_fan_out = metrics.get("top_fan_out", []) or []

    lines: List[str] = []
    lines.append("\n## Dependency outline\n")
    lines.append("- Graph summary:\n")
    lines.append(f"  - Nodes: {len(fan_in)}\n")
    # Sum in-degrees defensively (values may be ints or pair-like)
    try:
        edge_count = sum(_as_int(v) for v in fan_in.values())
    except Exception:
        edge_count = 0
    lines.append(f"  - Edges: {edge_count}\n")

    lines.append("- Top fan-in modules:\n")
    for n, v in list(top_fan_in)[:5]:
        lines.append(f"  - {n}: {_as_int(v)}\n")

    lines.append("- Top fan-out modules:\n")
    for n, v in list(top_fan_out)[:5]:
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
