from __future__ import annotations
import ast
from pathlib import Path
from typing import List
from cqia.parsing.ir import ModuleIR, FunctionIR, Span

BRANCH_NODES = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp, ast.IfExp)

def _get_source_segment(text: str, node: ast.AST) -> str:
    try:
        return ast.get_source_segment(text, node) or ""
    except Exception:
        return ""

def _complexity_count(node: ast.AST) -> int:
    count = 0
    for child in ast.walk(node):
        if isinstance(child, BRANCH_NODES):
            count += 1
        elif isinstance(child, ast.ExceptHandler):
            count += 1
    return count

def parse_python(path: Path, text: str) -> ModuleIR:
    tree = ast.parse(text)
    functions: List[FunctionIR] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            start = getattr(node, "lineno", 1)
            end = getattr(node, "end_lineno", start)
            doc = ast.get_docstring(node)
            body_text = _get_source_segment(text, node) or ""
            fn = FunctionIR(
                id=f"{path.as_posix()}::{name}:{start}",
                name=name,
                lang="python",
                span=Span(path=path, start_line=start, end_line=end),
                doc=doc,
                text=body_text,
                metrics={"complexity_branch_count": float(_complexity_count(node))}
            )
            functions.append(fn)
    return ModuleIR(path=path, lang="python", functions=functions)
