from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

def find_artifacts(scope: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Locate artifacts under scope or a sibling 'reports' directory:
    - report.md (Markdown summary)
    - report.json (or the most recent *.json) exported by exporters
    """
    scope = scope.resolve()
    candidates_md = [
        scope / "reports" / "report.md",
        scope / "report.md",
    ]
    candidates_json = [
        scope / "reports" / "report.json",
        scope / "report.json",
    ]

    report_md = next((p for p in candidates_md if p.exists()), None)

    report_json = next((p for p in candidates_json if p.exists()), None)
    if not report_json:
        # pick most recent *.json in reports if available
        rep_dir = scope / "reports"
        if rep_dir.exists():
            jsons = sorted(rep_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            report_json = jsons if jsons else None

    return report_md, report_json

def load_artifacts_text(report_md: Optional[Path], report_json: Optional[Path], max_chars: int = 80_000) -> str:
    """
    Load artifacts contents and return a trimmed textual block suitable for prompting.
    Priority: markdown first (human-readable), then JSON (as raw or summarized keys).
    """
    parts: list[str] = []
    if report_md and report_md.exists():
        try:
            text = report_md.read_text(encoding="utf-8", errors="ignore")
            if len(text) > max_chars:
                head = text[: max_chars // 2]
                tail = text[-max_chars // 2 :]
                text = f"{head}\n...\n{tail}"
            parts.append(f"# report.md\n{text}")
        except Exception:
            pass

    if report_json and report_json.exists():
        try:
            jtxt = report_json.read_text(encoding="utf-8", errors="ignore")
            if len(jtxt) > max_chars:
                head = jtxt[: max_chars // 2]
                tail = jtxt[-max_chars // 2 :]
                jtxt = f"{head}\n...\n{tail}"
            parts.append(f"# report.json\n{jtxt}")
        except Exception:
            pass

    return "\n\n".join(parts).strip()

def load_scope_findings(scope: Path, max_chars: int = 40_000) -> str:
    """
    Convenience wrapper to find artifacts under scope and load them into a single string.
    """
    md, js = find_artifacts(scope)
    return load_artifacts_text(md, js, max_chars=max_chars)
