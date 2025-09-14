from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal
import ast
import re

from cqia.parsing.ir import ModuleIR

# ---- Docstring detector (PEP 257) ----
@dataclass(frozen=True)
class DocFinding:
    id: str
    category: Literal["documentation"]
    message: str
    file: str
    start_line: int
    end_line: int
    kind: Literal["module", "class", "function"]

def detect_missing_docstrings(mod_path: Path, text: str) -> list[DocFinding]:
    out: list[DocFinding] = []
    try:
        tree = ast.parse(text or "")
    except Exception:
        return out

    # Module docstring
    mod_doc = ast.get_docstring(tree)
    if not mod_doc:
        out.append(DocFinding(
            id=f"{mod_path.as_posix()}::doc:module",
            category="documentation",
            message="Missing module docstring",
            file=mod_path.as_posix(),
            start_line=1,
            end_line=1,
            kind="module",
        ))

    # Classes and functions/methods
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if not ast.get_docstring(node):
                out.append(DocFinding(
                    id=f"{mod_path.as_posix()}::doc:class:{node.name}:{getattr(node, 'lineno', 1)}",
                    category="documentation",
                    message=f"Missing class docstring: {node.name}",
                    file=mod_path.as_posix(),
                    start_line=int(getattr(node, "lineno", 1)),
                    end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 1))),
                    kind="class",
                ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not ast.get_docstring(node):
                out.append(DocFinding(
                    id=f"{mod_path.as_posix()}::doc:function:{node.name}:{getattr(node, 'lineno', 1)}",
                    category="documentation",
                    message=f"Missing function/method docstring: {node.name}",
                    file=mod_path.as_posix(),
                    start_line=int(getattr(node, "lineno", 1)),
                    end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 1))),
                    kind="function",
                ))
    return out

# ---- Testing gaps (pytest conventions) ----
@dataclass(frozen=True)
class TestGapFinding:
    id: str
    category: Literal["testing"]
    message: str
    file: str
    expected_test: str
    hint: str

_PYTEST_FILE_PATTERNS = (
    "tests/test_{name}.py",
    "tests/{pkg}/test_{name}.py",
    "tests/{name}_test.py",
    "tests/{pkg}/{name}_test.py",
)

def expected_test_paths(src_rel: Path) -> list[Path]:
    # Derive a package-ish path for nested modules
    name = src_rel.stem
    pkg = src_rel.parent.as_posix()
    patterns = []
    for pat in _PYTEST_FILE_PATTERNS:
        patterns.append(Path(pat.format(name=name, pkg=pkg)))
    # Also consider colocated tests: same dir as source
    patterns.append(src_rel.parent / f"test_{name}.py")
    patterns.append(src_rel.parent / f"{name}_test.py")
    # Deduplicate
    seen = set()
    out: list[Path] = []
    for p in patterns:
        s = p.as_posix()
        if s not in seen:
            seen.add(s)
            out.append(p)
    return out

def detect_test_gaps(repo_root: Path, src_files: list[Path]) -> list[TestGapFinding]:
    out: list[TestGapFinding] = []
    # Only consider Python source files that are not already tests
    for src in src_files:
        if src.suffix != ".py":
            continue
        if src.name.startswith("test_") or src.name.endswith("_test.py"):
            continue
        # Skip obvious non-source directories
        rel = src
        candidates = expected_test_paths(rel)
        found = False
        for cand in candidates:
            if (repo_root / cand).exists():
                found = True
                break
        if not found:
            hint = "Create a pytest file like tests/test_{name}.py and add at least one test.".format(name=rel.stem)
            out.append(TestGapFinding(
                id=f"{rel.as_posix()}::testgap",
                category="testing",
                message=f"No test file found for {rel.as_posix()}",
                file=rel.as_posix(),
                expected_test=str(candidates),
                hint=hint,
            ))
    return out

# ---- Orchestrator used by runner ----
def run_testing_and_docs(root: Path, modules: Iterable[ModuleIR]) -> tuple[list[DocFinding], list[TestGapFinding]]:
    docs: list[DocFinding] = []
    for mod in modules:
        fpath = root / mod.path
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        if mod.lang == "python":
            docs.extend(detect_missing_docstrings(mod.path, text))

    # Build src file list (relative paths)
    src_files = [m.path for m in modules if m.lang == "python"]
    gaps = detect_test_gaps(root, src_files)
    return docs, gaps
