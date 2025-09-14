from __future__ import annotations
import ast
import re
from pathlib import Path
from typing import Literal

Lang = Literal["python", "javascript", "typescript", "unknown"]

_ESM_IMPORT_RE = re.compile(
    r'^\s*import\s+(?:[\w\{\}\*,\s]+)\s+from\s+[\'"]([^\'"]+)[\'"];?'
    r'|^\s*import\s+[\'"]([^\'"]+)[\'"];?',
    re.MULTILINE
)

def _s(x) -> str:
    return str(x)

def _py_imports(text: str) -> set[str]:
    try:
        tree = ast.parse(text or "")
    except Exception:
        return set()
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = (alias.name or "").split(".")
                if base:
                    deps.add(_s(base))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level and not mod:
                continue
            if mod:
                deps.add(_s(mod.split(".")))
    return deps

def _js_imports(text: str) -> set[str]:
    deps: set[str] = set()
    for m in _ESM_IMPORT_RE.finditer(text or ""):
        source = (m.group(1) or m.group(2) or "").strip()
        if not source:
            continue
        if source.startswith("."):
            parts = re.split(r"[\\/]", source)
            for p in parts:
                if p and p not in {".", ".."}:
                    deps.add(_s(p))
                    break
        else:
            deps.add(_s(source.split("/")))
    return deps

def read_imports(path: Path, lang: Lang, root: Path) -> set[str]:
    try:
        text = (root / path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()
    if lang == "python":
        return _py_imports(text)
    elif lang in {"javascript", "typescript"}:
        return _js_imports(text)
    return set()
