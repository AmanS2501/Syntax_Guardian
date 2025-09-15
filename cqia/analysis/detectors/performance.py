from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import ast
from cqia.parsing.ir import FunctionIR

IO_FUNCS = {
    ("", "open"),
    ("os", "remove"), ("os", "rename"), ("os", "replace"), ("os", "listdir"),
    ("shutil", "copy"), ("shutil", "copy2"), ("shutil", "copyfile"), ("shutil", "move"),
    ("pathlib.Path", "read_text"), ("pathlib.Path", "write_text"),
}
REQUESTS_FUNCS = {
    ("requests", "get"), ("requests", "post"), ("requests", "put"),
    ("requests", "delete"), ("requests", "head"), ("requests", "patch"),
}

@dataclass(frozen=True)
class PerfFinding:
    id: str
    category: str
    message: str
    file: str
    start_line: int
    end_line: int
    hint: str
    kind: str

class _PerfVisitor(ast.NodeVisitor):
    def __init__(self, src_path: Path, text: str):
        self.src_path = src_path
        self.text = text
        self.findings: list[PerfFinding] = []
        self._loop_depth = 0

    def _call_target(self, node: ast.Call) -> tuple[str, str] | None:
        func = node.func
        if isinstance(func, ast.Name):
            return ("", func.id)
        if isinstance(func, ast.Attribute):
            parts = []
            cur = func
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            parts.reverse()
            if not parts:
                return None
            qual = ".".join(parts[:-1]) if len(parts) > 1 else parts
            name = parts[-1]
            return (qual, name)
        return None

    def _mark(self, kind: str, node: ast.AST, msg: str, hint: str):
        self.findings.append(PerfFinding(
            id=f"{self.src_path.as_posix()}::{kind}:{getattr(node, 'lineno', 1)}",
            category="performance",
            message=msg,
            file=self.src_path.as_posix(),
            start_line=int(getattr(node, "lineno", 1)),
            end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 1))),
            hint=hint,
            kind=kind
        ))

    def visit_For(self, node: ast.For):
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node: ast.While):
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_Call(self, node: ast.Call):
        if self._loop_depth > 0:
            tgt = self._call_target(node)
            if tgt:
                qual, name = tgt
                if (qual, name) in REQUESTS_FUNCS:
                    self._mark("requests_in_loop", node,
                               "HTTP request inside loop; consider batching or concurrency",
                               "Use requests.Session for pooling or asyncio/httpx to parallelize.")
                elif (qual, name) in IO_FUNCS or (name in {"read_text", "write_text"} and "Path" in qual):
                    self._mark("io_in_loop", node,
                               "File I/O inside loop; hoist reads/writes or buffer",
                               "Read outside the loop or batch writes; flush once.")
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        if self._loop_depth > 0 and isinstance(node.op, ast.Add):
            self._mark("string_concat_in_loop", node,
                       "String concatenation in loop; use list append + ''.join(...)",
                       "Append to a list inside loop, then s=''.join(parts) once.")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if self._loop_depth > 0 and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
            if node.targets and isinstance(node.targets, ast.Name) and isinstance(node.value.left, ast.Name):
                if node.targets.id == node.value.left.id:
                    self._mark("string_concat_in_loop", node,
                               "String concatenation in loop; use list append + ''.join(...)",
                               "Append to a list inside loop, then s=''.join(parts) once.")
        self.generic_visit(node)

def detect_performance(functions: Iterable[FunctionIR], root: Path) -> list[PerfFinding]:
    out: list[PerfFinding] = []
    for fn in functions:
        fpath = root / fn.span.path
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except Exception:
            continue
        v = _PerfVisitor(fn.span.path, text)
        v.visit(tree)
        for f in v.findings:
            if fn.span.start_line <= f.start_line <= fn.span.end_line:
                out.append(f)
    return out
